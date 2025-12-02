#!/usr/bin/env python3
"""
Generate TTS audio files for Remotion video narration.
Uses macOS built-in 'say' command for text-to-speech.
"""

import json
import subprocess
import os

def generate_tts_audio():
    # Load narration script
    with open('src/narration-script.json', 'r') as f:
        script_data = json.load(f)
    
    # Create audio directory if it doesn't exist
    os.makedirs('src/audio', exist_ok=True)
    
    # Voice options: Alex (default male), Samantha (female), Daniel (UK male)
    voice = "Alex"
    
    for slide in script_data['slides']:
        slide_num = slide['slide']
        narration = slide['narration']
        
        # Generate audio file name
        audio_file = f"src/audio/slide-{slide_num}-narration.aiff"
        
        print(f"Generating audio for slide {slide_num}...")
        
        # Use macOS 'say' command to generate speech
        # -v: voice, -o: output file, -r: rate (words per minute)
        cmd = [
            'say', 
            '-v', voice,
            '-r', '160',  # Speaking rate
            '-o', audio_file,
            narration
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"✓ Generated: {audio_file}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Error generating {audio_file}: {e}")
    
    print("\nTTS audio generation complete!")
    print("Audio files are ready to be integrated into Remotion.")

if __name__ == "__main__":
    generate_tts_audio()