#!/usr/bin/env python3
"""
Convert AIFF audio files to WAV format for better compatibility with Remotion.
"""

import json
import subprocess
import os

def convert_audio_files():
    # Load narration script
    with open('src/narration-script.json', 'r') as f:
        script_data = json.load(f)
    
    # Create audio directory if it doesn't exist
    os.makedirs('public/audio', exist_ok=True)
    
    for slide in script_data['slides']:
        slide_num = slide['slide']
        
        # Input and output file names
        input_file = f"src/audio/slide-{slide_num}-narration.aiff"
        output_file = f"public/audio/slide-{slide_num}-narration.wav"
        
        print(f"Converting slide {slide_num} audio to WAV...")
        
        # Use ffmpeg to convert AIFF to WAV
        cmd = [
            'ffmpeg', '-y',  # -y to overwrite existing files
            '-i', input_file,
            '-acodec', 'pcm_s16le',  # 16-bit PCM WAV
            '-ar', '44100',  # 44.1kHz sample rate
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✓ Converted: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Error converting {input_file}: {e}")
            print(f"  Error output: {e.stderr.decode() if e.stderr else 'None'}")
    
    print("\nAudio conversion complete!")
    print("WAV files are ready for Remotion.")

if __name__ == "__main__":
    convert_audio_files()