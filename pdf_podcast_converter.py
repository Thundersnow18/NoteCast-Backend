import os
import json
from pathlib import Path
import PyPDF2
import requests

class PDFToPodcastConverter:
    """
    Converts PDF documents into engaging multi-speaker podcast format.
    Uses free local AI models (Ollama) and Edge TTS.
    """
    
    def __init__(self, openai_api_key=None, elevenlabs_api_key=None, anthropic_api_key=None):
        """Initialize - no API keys needed!"""
        self.ollama_url = "http://localhost:11434/api/generate"
        print("[OK] Using free local AI models")
        
    def extract_text_from_pdf(self, pdf_path, max_pages=None):
        """Extract text content from PDF up to max_pages."""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            pages_to_read = min(total_pages, max_pages) if max_pages else total_pages
            for i in range(pages_to_read):
                page_text = pdf_reader.pages[i].extract_text()
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
    
    def _build_prompt(self, text_sample, preferences):
        """Build customized prompt based on user preferences."""
        
        # Base personality descriptions
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
        
        # Length guidelines
        length_guides = {
            'short': '4-6 quick exchanges, hit the main points',
            'medium': '8-10 exchanges, cover key concepts with some depth',
            'long': '12-15 exchanges, thorough exploration with examples'
        }
        
        # Depth levels
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
            humor_instruction = "\n- Add occasional light humor, relatable analogies, and personality\n- Make it engaging and enjoyable, not dry"
        
        prompt = f"""You are a podcast script writer. Create a {tone} conversation between HOST and EXPERT.

HOST personality: {tone_style['host']}
EXPERT personality: {tone_style['expert']}

Style: {tone_style['style']}

Length: {length_guides[length]}
Depth: {depth_guides[depth]}{humor_instruction}

STRICT FORMAT - Each line must start with HOST: or EXPERT:

Example:
HOST: Welcome! What fascinating insights do we have today?
EXPERT: We're diving into some really interesting concepts from this document.
HOST: I'm intrigued! Break it down for me.
EXPERT: Let me explain the key ideas in a way that makes sense.

Content to discuss:
{text_sample}

Create the podcast dialogue following the format above:"""
        
        return prompt
    
    def generate_podcast_script(self, text, preferences=None):
        """Generate script using free local Ollama with custom preferences."""
        
        if preferences is None:
            preferences = {}
        
        
        text_sample = text[:8000].strip()
        
        prompt = self._build_prompt(text_sample, preferences)
        
        length_tokens = {
            'short': 600,
            'medium': 950,
            'long': 1400
        }
        max_tokens = length_tokens.get(preferences.get('length', 'medium'), 950)
        
        try:
            print(f"Generating {preferences.get('tone', 'conversational')} script with Ollama (llama3.2:latest, 4k ctx)...")
            response = requests.post(
                self.ollama_url,
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.85 if preferences.get('humor') else 0.7,
                        "num_predict": max_tokens,
                        "stop": ["USER:", "ASSISTANT:"],
                        "num_ctx": 4096
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                script = response.json()['response']
                
                print("\n" + "="*60)
                print("RAW SCRIPT FROM OLLAMA:")
                print("="*60)
                print(script[:500])
                print("="*60 + "\n")
                
                return script
            else:
                print(f"✗ Ollama HTTP error: {response.status_code} - {response.text}")
                return self._create_fallback_script(text)
                
        except Exception as e:
            print(f"✗ Ollama connection error: {e}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_script(text)
    
    def _create_fallback_script(self, text):
        """Create a detailed script if Ollama fails."""
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
        """Parse the script into speaker-dialogue pairs using regex flexibility."""
        import re
        lines = script.strip().split('\n')
        dialogue = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Match formats like HOST:, **HOST:**, Host:, **Host:**, EXPERT:, **EXPERT:**
            match = re.match(r'^\s*(?:\*\*)?(HOST|EXPERT|Host|Expert)(?:\*\*)?\s*:\s*(.*)', line, re.IGNORECASE)
            
            if match:
                speaker_raw = match.group(1).upper()
                text_content = match.group(2).strip()
                
                speaker = 'HOST' if 'HOST' in speaker_raw else 'EXPERT'
                
                if text_content:
                    dialogue.append({
                        'speaker': speaker,
                        'text': text_content
                    })
            elif line and dialogue:
                # Append multi-line spoken content to current speaker
                # Ignore meta introductory lines before first speaker tag
                cleaned_line = line.replace('**', '').replace('*', '').strip()
                if not cleaned_line.startswith(('Here is', 'Sure', 'Note:', 'Podcast Script')):
                    dialogue[-1]['text'] += ' ' + cleaned_line
        
        cleaned_dialogue = []
        for entry in dialogue:
            text = entry['text'].strip()
            text = text.replace('**', '').replace('*', '').strip()
            
            # Remove any trailing orphan speaker labels (e.g. text ending with 'HOST:' or 'HOST')
            text = re.sub(r'\s*(?:HOST|EXPERT)\s*:?\s*$', '', text, flags=re.IGNORECASE).strip()
            
            # Ensure text is not just a speaker label or empty
            if len(text) > 3 and text.upper() not in ['HOST', 'EXPERT', 'HOST:', 'EXPERT:']:
                cleaned_dialogue.append({
                    'speaker': entry['speaker'],
                    'text': text
                })
        
        print(f"\n[OK] Parsed {len(cleaned_dialogue)} dialogue segments")
        
        for i, seg in enumerate(cleaned_dialogue[:3]):
            print(f"  {i+1}. {seg['speaker']}: {seg['text'][:60]}...")
        
        if not cleaned_dialogue:
            print("[WARN] No dialogue parsed from LLM output, using fallback script")
            cleaned_dialogue = [
                {'speaker': 'HOST', 'text': 'Welcome to this podcast episode about your document.'},
                {'speaker': 'EXPERT', 'text': 'Thank you for having me. Let me share the key insights from this material.'}
            ]
        
        return cleaned_dialogue
    
    def synthesize_speech(self, dialogue, output_dir="podcast_output"):
        """Convert dialogue to speech using Edge TTS with automated retry & fallback voices."""
        import asyncio
        import edge_tts
        import random
        import re
        
        Path(output_dir).mkdir(exist_ok=True)
        
        # High-stability, verified natural expressive neural voices from Edge TTS
        male_voices = [
            'en-US-GuyNeural',         # Ultra-reliable, natural US Male
            'en-US-BrianNeural',       # Warm US Male
            'en-US-ChristopherNeural', # Deep, clear US Male
            'en-GB-RyanNeural',        # Professional UK Male
        ]
        
        female_voices = [
            'en-US-AriaNeural',        # Ultra-reliable, expressive US Female
            'en-US-JennyNeural',       # Friendly, clear US Female
            'en-US-EmmaNeural',        # Conversational US Female
            'en-GB-SoniaNeural',       # Smooth UK Female
        ]
        
        # 50% chance: Host=Male, Expert=Female; 50% chance: Host=Female, Expert=Male
        if random.choice([True, False]):
            host_voice = random.choice(male_voices)
            expert_voice = random.choice(female_voices)
        else:
            host_voice = random.choice(female_voices)
            expert_voice = random.choice(male_voices)
            
        voices = {
            'HOST': host_voice,
            'EXPERT': expert_voice
        }
        
        # Rock-solid fallback voices if the primary chosen voice hits server throttling
        fallback_voices = {
            'HOST': 'en-US-GuyNeural' if 'Female' in host_voice else 'en-US-AriaNeural',
            'EXPERT': 'en-US-AriaNeural' if 'Male' in expert_voice else 'en-US-GuyNeural'
        }
        
        print(f"\n[VOICES] HOST: {voices['HOST']} | EXPERT: {voices['EXPERT']}")
        print(f"Generating audio with Edge TTS for {len(dialogue)} segments...")
        
        def clean_for_tts(raw_text):
            # Remove stage directions like (laughs), [applause], *chuckles*, *giggles*
            text = re.sub(r'[\(\[\*][^\)\]\*]*[\)\]\*]', '', raw_text)
            # Remove XML/HTML tags
            text = re.sub(r'[<>]', '', text)
            # Replace ampersands with words
            text = text.replace('&', ' and ')
            # Clean whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        async def run_batch_synthesis():
            audio_files = []
            
            for idx, segment in enumerate(dialogue):
                speaker = segment['speaker']
                raw_text = segment['text']
                
                clean_text = clean_for_tts(raw_text)
                if not clean_text or len(clean_text) < 2:
                    clean_text = "Indeed."
                
                filename = f"{output_dir}/segment_{idx:03d}_{speaker}.mp3"
                print(f"  [{idx + 1}/{len(dialogue)}] {speaker}: {clean_text[:50]}...")
                
                success = False
                max_attempts = 4
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        # Attempts 1-2: use primary chosen voice. Attempts 3-4: use fallback voice.
                        voice_to_use = voices[speaker] if attempt <= 2 else fallback_voices[speaker]
                        
                        communicate = edge_tts.Communicate(clean_text, voice_to_use)
                        await communicate.save(filename)
                        
                        if os.path.exists(filename) and os.path.getsize(filename) > 200:
                            audio_files.append(filename)
                            print(f"    [OK] Generated ({os.path.getsize(filename)} bytes)")
                            success = True
                            break
                        else:
                            print(f"    [FAIL] Empty audio file received (attempt {attempt}/{max_attempts})")
                            await asyncio.sleep(1.0 * attempt)
                    except Exception as e:
                        print(f"    [FAIL] TTS network retry ({attempt}/{max_attempts}): {e}")
                        await asyncio.sleep(1.5 * attempt)
                
                if not success:
                    print(f"    [WARN] Segment {idx + 1} could not be synthesized after {max_attempts} attempts.")
            
            return audio_files

        audio_files = asyncio.run(run_batch_synthesis())
        print(f"\n[OK] Successfully generated {len(audio_files)}/{len(dialogue)} audio segments")
        return audio_files
    
    def combine_audio_files(self, audio_files, output_path="final_podcast.mp3"):
        """Combine all audio segments using ffmpeg directly."""
        if not audio_files:
            print("No audio files to combine!")
            return None
        
        print(f"\n[AUDIO] Combining {len(audio_files)} audio segments...")
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
                    print(f"  Appending {i+1}/{len(audio_files)}: {os.path.basename(audio_file)}")
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
    
    def summarize_section(self, section_text):
        """Map Phase: Extract dense, high-signal bullet takeaways from a document section."""
        prompt = f"""You are an executive research analyst. Extract the 2-3 most important findings, arguments, or insights from this document excerpt.
Be factual, dense, and concise (bullet points only).

Document Excerpt:
{section_text[:3500]}

Key Takeaways:"""
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 90,
                        "stop": ["USER:", "ASSISTANT:", "Document Excerpt:"],
                        "num_ctx": 4096
                    }
                },
                timeout=45
            )
            if response.status_code == 200:
                summary = response.json().get('response', '').strip()
                if summary:
                    return summary
        except Exception as e:
            print(f"  ⚠ Section summarization failed: {e}")
        
        # Fallback snippet
        return f"- {section_text[:200].replace(chr(10), ' ')}"

    def reduce_summaries(self, section_summaries):
        """Reduce Phase: Combine section summaries into a master thematic outline."""
        combined_text = "\n\n".join(section_summaries)
        
        if len(combined_text) <= 2500:
            return combined_text
            
        print("  🔄 Reducing multiple section summaries into a unified master outline...")
        prompt = f"""Synthesize and consolidate the following section keypoints from a full document into a unified master outline.
Organize into cohesive themes: Main Thesis, Key Evidence/Arguments, and Conclusions/Implications.

Section Keypoints:
{combined_text[:4000]}

Unified Master Outline:"""
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.4,
                        "num_predict": 300,
                        "stop": ["USER:", "ASSISTANT:"],
                        "num_ctx": 4096
                    }
                },
                timeout=60
            )
            if response.status_code == 200:
                reduced = response.json().get('response', '').strip()
                if reduced:
                    return reduced
        except Exception as e:
            print(f"  ⚠ Reduce phase failed: {e}")
            
        return combined_text[:2500]

    def extract_strategic_slices(self, full_text, max_slices=4, slice_size=3500):
        """Extract up to max_slices evenly distributed across documents of any length."""
        total_len = len(full_text)
        if total_len <= slice_size * max_slices:
            return self.chunk_text(full_text, max_chars=slice_size)
            
        slices = []
        step = (total_len - slice_size) / (max_slices - 1)
        for i in range(max_slices):
            start_idx = int(i * step)
            end_idx = min(start_idx + slice_size, total_len)
            slice_text = full_text[start_idx:end_idx].strip()
            if slice_text:
                slices.append(slice_text)
        return slices

    def map_reduce_document(self, full_text):
        """Adaptive pipeline: Single-pass fast lane for <=12k chars, or smart 4-slice Map-Reduce for large/mega docs."""
        total_chars = len(full_text)
        
        # 1. FAST LANE: <= 12,000 characters (~5-8 pages) -> Ingest directly in 1 single LLM call!
        if total_chars <= 12000:
            print(f"⚡ [Fast-Lane Engine] Document is {total_chars} chars (~{max(1, round(total_chars/2500, 1))} pages). Processing in 1 direct single pass!")
            return full_text
            
        # 2. STRATIFIED SAMPLING FOR LARGE / MEGA DOCUMENTS (50 to 6,000+ pages)
        print(f"\n🗺️  [Large Document Engine] Document has {total_chars} chars (~{round(total_chars/2500)} pages).")
        print(f"   ↳ Taking 4 strategic high-signal slices across Introduction, Body, and Conclusion...")
        
        slices = self.extract_strategic_slices(full_text, max_slices=4, slice_size=3500)
        
        section_summaries = []
        labels = ["Opening / Introduction", "Core Arguments (1/3)", "Evidence & Analysis (2/3)", "Conclusions & Takeaways"]
        for idx, slice_content in enumerate(slices):
            label = labels[idx] if idx < len(labels) else f"Section {idx+1}"
            print(f"   ↳ Summarizing {label} ({idx + 1}/{len(slices)})...")
            summary = self.summarize_section(slice_content)
            section_summaries.append(f"### {label}:\n{summary}")
            
        print(f"\n[Reduce Phase] Synthesizing master outline from {len(section_summaries)} sections...")
        master_outline = self.reduce_summaries(section_summaries)
        print(f"[OK] Master document outline synthesized ({len(master_outline)} chars)")
        return master_outline

    def convert_pdf_to_podcast(self, pdf_path, output_path="podcast.mp3", max_pages=None, preferences=None):
        """Main method: Convert PDF of any length to complete podcast with adaptive fast-lane."""
        if preferences is None:
            preferences = {}
        
        print(f"Extracting text from PDF: {pdf_path}")
        print(f"Preferences: {preferences}")
        
        text = self.extract_text_from_pdf(pdf_path, max_pages=max_pages)
        print(f"Extracted {len(text)} characters from document")
        
        if not text.strip():
            raise ValueError("No extractable text found in PDF. It might be scanned/image-only.")

        # Adaptive Map-Reduce / Fast Lane
        master_content = self.map_reduce_document(text)
        
        print("\nGenerating comprehensive podcast script from full document context...")
        script = self.generate_podcast_script(master_content, preferences)
        all_dialogue = self.parse_dialogue(script)
        
        script_path = output_path.replace('.mp3', '_script.json')
        with open(script_path, 'w') as f:
            json.dump(all_dialogue, f, indent=2)
        print(f"[OK] Script saved to: {script_path}")
        
        print(f"\nSynthesizing speech with Edge TTS...")
        audio_files = self.synthesize_speech(all_dialogue, output_dir=os.path.dirname(output_path) or ".")
        
        print(f"\n🎧 Combining audio segments...")
        final_path = self.combine_audio_files(audio_files, output_path)
        
        return {
            'output_path': final_path,
            'transcript': all_dialogue
        }