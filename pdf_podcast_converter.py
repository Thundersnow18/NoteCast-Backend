import os
import json
from pathlib import Path
import PyPDF2
import time
import re
from groq import Groq, RateLimitError
from typing import Any, Dict, List, Optional, Tuple 

class PDFToPodcastConverter:
    """
    Converts PDF documents into engaging multi-speaker podcast format.
    Uses free local AI models (Ollama) and Edge TTS.
    """
    
    def __init__(self, openai_api_key=None, elevenlabs_api_key=None, anthropic_api_key=None):
        """Initialize - now uses Groq API Key."""
        
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("⚠️ WARNING: GROQ_API_KEY environment variable not found. Script generation will fail.")
        
        # We don't need the Ollama URL anymore.
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.model_id = "llama-3.1-8b-instant" # Ultra-fast and great for this task
        
        print(f"✓ Using Groq API ({self.model_id}) for script generation")
        
    def extract_text_from_pdf(self, pdf_path):
        """Extract all text content from PDF file."""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def chunk_text(self, text, max_chars=3000):
        """Split text into manageable chunks for processing."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1
            if current_length + word_length > max_chars and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    # --- UPDATED: Added section_num and total_sections for continuity ---
    def _build_prompt(self, text_sample, preferences, section_num=1, total_sections=1):
        """Build customized prompt based on user preferences and section context."""
        
        tone_styles = {
            'casual': {
                'host': 'friendly, enthusiastic, uses casual language like "you know", "pretty cool"',
                'expert': 'knowledgeable but relaxed, explains things like talking to a friend',
                'style': 'Keep it light and fun, like friends chatting over coffee'
            },
            'conversational': {
                'host': 'engaging and curious, asks thoughtful questions',
                'expert': 'clear and articulate, good at explaining concepts',
                'style': 'Natural conversation with good flow'
            },
            'professional': {
                'host': 'well-prepared, asks insightful questions',
                'expert': 'authoritative and precise, provides detailed explanations',
                'style': 'Professional but accessible, like a quality educational podcast'
            }
        }
        
        length_guides = {
            'short': '4-6 quick exchanges, hit the main points',
            'medium': '8-10 exchanges, cover key concepts with some depth',
            'long': '12-15 exchanges, thorough exploration with examples'
        }
        
        depth_guides = {
            'overview': 'Focus on high-level takeaways and main ideas',
            'balanced': 'Balance overview with some detailed explanations and examples',
            'deep-dive': 'Provide thorough explanations, examples, and explore nuances'
        }
        
        tone = preferences.get('tone', 'conversational')
        length = preferences.get('length', 'medium')
        depth = preferences.get('depth', 'balanced')
        humor = preferences.get('humor', True)
        
        tone_style = tone_styles.get(tone, tone_styles['conversational'])
        
        humor_instruction = ""
        if humor:
            humor_instruction = "\n- Add occasional light humor, relatable analogies, and personality\n- Make it engaging and enjoyable, not dry\n- CRITICAL: DO NOT WRITE STAGE DIRECTIONS LIKE (LAUGHS), [CHUCKLES], or [MUSIC]—only write dialogue."
        
        # --- Continuity Instructions ---
        continuity_instruction = ""
        if total_sections > 1:
            if section_num == 1:
                continuity_instruction = "Since this is the first section, the HOST should open the podcast with a warm welcome and an overview."
            elif section_num < total_sections:
                continuity_instruction = "This is a middle section. The conversation must **START IN MEDIA RES (mid-conversation)**. The HOST should transition smoothly from the previous segment's topic to introduce this new content."
            else: # last section
                continuity_instruction = "This is the final section. The conversation must **START IN MEDIA RES**. The final exchange must be a clear wrap-up and conclusion, with the HOST thanking the EXPERT."
        # --------------------------------------

        prompt = f"""You are a podcast script writer. Create a {tone} conversation between HOST and EXPERT.
        
{continuity_instruction} 

HOST personality: {tone_style['host']}
EXPERT personality: {tone_style['expert']}

Style: {tone_style['style']}

Length: {length_guides[length]}
Depth: {depth_guides[depth]}{humor_instruction}

STRICT FORMAT - Each line must start with HOST: or EXPERT:

Example (for non-final section):
HOST: That connects perfectly to our next topic, the rise of quantum computing.
EXPERT: Indeed, that's where the real complexity begins.

Content to discuss (Section {section_num} of {total_sections}):
{text_sample}

Create the podcast dialogue following the format above:"""
        
        return prompt
    
    # --- UPDATED: Switched from Ollama requests to Groq SDK ---
    def generate_podcast_script(self, text, preferences=None, section_num=1, total_sections=1):
        """Generate script using Groq SDK with custom preferences."""
        
        if preferences is None:
            preferences = {}
        
        if not self.client:
            print("✗ Groq client not initialized. Using fallback script.")
            return self._create_fallback_script(text)
        
        text_sample = text[:2000].replace('\n', ' ')
        prompt = self._build_prompt(text_sample, preferences, section_num, total_sections)
        
        length_tokens = {
            'short': 600,
            'medium': 1000,
            'long': 1500
        }
        max_tokens = length_tokens.get(preferences.get('length', 'medium'), 1000)
        
        messages = [
            {"role": "user", "content": prompt}
        ]

        try:
            print(f"⚡ Generating {preferences.get('tone', 'conversational')} script with Groq...")
            
            completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model_id,
                temperature=0.9 if preferences.get('humor') else 0.7,
                max_tokens=max_tokens,
            )
            
            script = completion.choices[0].message.content
            
            print("\n" + "="*60)
            print(f"RAW SCRIPT FROM GROQ ({len(script)} chars):")
            print("="*60)
            print(script[:500])
            print("="*60 + "\n")
            
            return script
                
        except RateLimitError as e:
            print(f"✗ Groq Rate Limit Error (429): {e}")
            # This is critical: When you hit the limit, you must handle it gracefully.
            print("⚠️ Recommending a short delay before trying the next chunk.")
            return self._create_fallback_script(text)
            
        except Exception as e:
            print(f"✗ Groq API Error: {e}")
            return self._create_fallback_script(text)
    
    def _create_fallback_script(self, text):
        """Create a detailed script if LLM fails."""
        text_snippet = text[:200].replace('\n', ' ')
        
        return f"""HOST: Welcome everyone to today's episode! We're diving into some really interesting material.
EXPERT: Thank you for having me! I'm excited to break down these concepts for your listeners.
HOST: Let's start with the basics. What's the main topic we're covering today?
EXPERT: This content focuses on {text_snippet}. It's a fascinating subject with practical applications.
HOST: That sounds intriguing! Can you elaborate on the key points?
EXPERT: Absolutely. The first major concept revolves around understanding the fundamental principles and how they interconnect.
HOST: How does this apply in real-world scenarios?
EXPERT: Great question! In practice, these ideas help us solve complex problems by providing a structured framework.
HOST: Are there any common misconceptions people have about this topic?
EXPERT: Yes, many people initially think it's more complicated than it actually is. Once you understand the core ideas, everything else falls into place.
HOST: That's really helpful context. What should listeners remember most?
EXPERT: The key takeaway is that mastering the basics opens doors to understanding the more advanced concepts. Start simple and build from there.
HOST: Excellent advice! Thank you so much for sharing your insights.
EXPERT: My pleasure! I hope this has been valuable for everyone listening."""
    
    def parse_dialogue(self, script):
        """Parse the script into speaker-dialogue pairs and strip stage directions."""
        lines = script.strip().split('\n')
        dialogue = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
                
            if line.startswith('HOST:'):
                text = line.replace('HOST:', '').strip()
                if text:
                    dialogue.append({'speaker': 'HOST', 'text': text})
            elif line.startswith('EXPERT:'):
                text = line.replace('EXPERT:', '').strip()
                if text:
                    dialogue.append({'speaker': 'EXPERT', 'text': text})
            elif line and dialogue:
                # Continue previous speaker's dialogue
                dialogue[-1]['text'] += ' ' + line
        
        # Clean up and validate
        cleaned_dialogue = []
        for entry in dialogue:
            text = entry['text'].strip()
            text = text.replace('**', '').replace('*', '')
            
            # Strip common stage directions (Fix 1 from previous)
            text = re.sub(r'\([^)]*\)', '', text)
            text = re.sub(r'\[[^\]]*\]', '', text)
            text = re.sub(r'<[^>]*>', '', text)
            
            # Clean up residual whitespace/punctuation
            text = text.strip().replace('...', '').strip()
            
            if len(text) > 5:
                cleaned_dialogue.append({
                    'speaker': entry['speaker'],
                    'text': text
                })
        
        print(f"\n✓ Parsed {len(cleaned_dialogue)} dialogue segments")
        
        for i, seg in enumerate(cleaned_dialogue[:3]):
            print(f"  {i+1}. {seg['speaker']}: {seg['text'][:60]}...")
        
        if not cleaned_dialogue:
            print("⚠ No dialogue parsed, using fallback")
            cleaned_dialogue = [
                {'speaker': 'HOST', 'text': 'Welcome to this podcast episode about your document.'},
                {'speaker': 'EXPERT', 'text': 'Thank you for having me. Let me share the key insights from this material.'}
            ]
        
        return cleaned_dialogue
    
    def synthesize_speech(self, dialogue, output_dir="podcast_output"):
        """Convert dialogue to speech using Edge TTS (free, better quality)."""
        import asyncio
        import edge_tts
        
        Path(output_dir).mkdir(exist_ok=True)
        audio_files = []
        
        voices = {
            'HOST': 'en-US-GuyNeural',
            'EXPERT': 'en-US-JennyNeural'
        }
        
        async def generate_audio(text, voice, filename):
            """Generate single audio file."""
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filename)
        
        print(f"\n🎵 Generating audio with Edge TTS for {len(dialogue)} segments...")
        
        for idx, segment in enumerate(dialogue):
            speaker = segment['speaker']
            text = segment['text']
            
            if not text or len(text.strip()) < 3:
                print(f"  Skipping empty segment {idx + 1}")
                continue
            
            print(f"  [{idx + 1}/{len(dialogue)}] {speaker}: {text[:50]}...")
            
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    filename = f"{output_dir}/segment_{idx:03d}_{speaker}.mp3"
                    
                    asyncio.run(generate_audio(text, voices[speaker], filename))
                    
                    if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                        audio_files.append(filename)
                        print(f"    ✓ Generated ({os.path.getsize(filename)} bytes)")
                        break
                    else:
                        print(f"    ✗ File too small (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                        
                except Exception as e:
                    print(f"    ✗ Error (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        print(f"    ✗ Failed after {max_retries} attempts, skipping segment")
        
        print(f"\n✓ Successfully generated {len(audio_files)} audio segments")
        return audio_files
    
    def combine_audio_files(self, audio_files, output_path="final_podcast.mp3"):
        """Combine all audio segments using ffmpeg directly."""
        if not audio_files:
            print("No audio files to combine!")
            return None
        
        print(f"\n🎧 Combining {len(audio_files)} audio segments...")
        print(f"Output: {output_path}")
        
        try:
            import subprocess
            
            list_file = output_path.replace('.mp3', '_filelist.txt')
            
            with open(list_file, 'w', encoding='utf-8') as f:
                for audio_file in audio_files:
                    abs_path = os.path.abspath(audio_file).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")
            
            print(f"✓ Created file list with {len(audio_files)} entries")
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            print(f"Running ffmpeg concat...")
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=60
            )
            
            if os.path.exists(list_file):
                os.remove(list_file)
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✓ Successfully combined! ({file_size:,} bytes)")
                return output_path
            else:
                print(f"✗ FFmpeg error (code {result.returncode}):")
                print(result.stderr[:500])
                raise Exception("FFmpeg combining failed")
                
        except subprocess.TimeoutExpired:
            print("✗ FFmpeg timed out")
            return self._fallback_combine(audio_files, output_path)
        except Exception as e:
            print(f"✗ Combining error: {e}")
            return self._fallback_combine(audio_files, output_path)

    def _fallback_combine(self, audio_files, output_path):
        """Fallback: create a simple concatenated file."""
        print("⚠ Falling back to simple binary concatenation...")
        
        try:
            with open(output_path, 'wb') as outfile:
                for i, audio_file in enumerate(audio_files):
                    print(f"  Appending {i+1}/{len(audio_files)}: {os.path.basename(audio_file)}")
                    with open(audio_file, 'rb') as infile:
                        outfile.write(infile.read())
            
            if os.path.exists(output_path):
                print(f"✓ Created concatenated file: {output_path}")
                return output_path
        except Exception as e:
            print(f"✗ Fallback failed: {e}")
        
        print("⚠ Using first segment only")
        if audio_files and os.path.exists(audio_files[0]):
            import shutil
            shutil.copy(audio_files[0], output_path)
            return output_path
        
        return None
    
    def convert_pdf_to_podcast(self, pdf_path, output_path="podcast.mp3", max_pages=None, preferences=None):
        """Main method: Convert PDF to complete podcast with user preferences."""
        
        if preferences is None:
            preferences = {}
        
        print(f"📄 Extracting text from PDF: {pdf_path}")
        print(f"🎨 Preferences: {preferences}")
        
        text = self.extract_text_from_pdf(pdf_path)
        
        if max_pages:
            text = text[:max_pages * 3000]
        
        print(f"📝 Extracted {len(text)} characters")
        
        chunk_size = {
            'short': 2000,
            'medium': 3000,
            'long': 4000
        }.get(preferences.get('length', 'medium'), 3000)
        
        chunks = self.chunk_text(text, max_chars=chunk_size)
        
        max_chunks = 1 if preferences.get('length') == 'short' else 2
        chunks = chunks[:max_chunks]
        
        total_chunks = len(chunks)
        print(f"📚 Processing {total_chunks} section(s)")
        
        all_dialogue = []
        
        for i, chunk in enumerate(chunks):
            print(f"\n🎙️  Generating podcast script for section {i+1}/{total_chunks}...")
            
            # --- API CALL IS HERE ---
            script = self.generate_podcast_script(
                chunk, 
                preferences, 
                section_num=i + 1, 
                total_sections=total_chunks
            )
            
            dialogue = self.parse_dialogue(script)
            all_dialogue.extend(dialogue)
            
            # Small delay between high-load API calls to prevent immediate rate limiting
            if i < total_chunks - 1:
                time.sleep(0.5) 
        
        # --- Ensure output directory exists before writing script ---
        output_dir = os.path.dirname(output_path) or "."
        Path(output_dir).mkdir(exist_ok=True, parents=True)
        
        script_filename = os.path.basename(output_path).replace('.mp3', '_script.json')
        script_path = os.path.join(output_dir, script_filename)
        with open(script_path, 'w') as f:
            json.dump(all_dialogue, f, indent=2)
        print(f"✓ Script saved to: {script_path}")
        
        print(f"\n🎵 Synthesizing speech with Edge TTS...")
        audio_files = self.synthesize_speech(all_dialogue, output_dir=output_dir)
        
        print(f"\n🎧 Combining audio segments...")
        final_path = self.combine_audio_files(audio_files, output_path)
        
        return {
            'output_path': final_path,
            'transcript': all_dialogue
        }