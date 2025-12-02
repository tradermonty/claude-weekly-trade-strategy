#!/usr/bin/env python3
"""
Generate high-quality Japanese TTS audio files using OpenAI's TTS API.
"""

import json
import os
import requests
import time
from pathlib import Path

def load_openai_api_key():
    """Load OpenAI API key from .env file."""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('OPENAI_API_KEY='):
                    return line.split('=', 1)[1].strip()
    
    # Try environment variable
    return os.environ.get('OPENAI_API_KEY')

def generate_japanese_tts():
    """Generate Japanese TTS audio files using OpenAI's API."""
    
    # Load API key
    api_key = load_openai_api_key()
    if not api_key:
        print("❌ OpenAI API key not found. Please check your .env file.")
        return
    
    # Load narration script
    with open('src/earnings-trade-narration.json', 'r', encoding='utf-8') as f:
        script_data = json.load(f)
    
    # Create audio directory
    os.makedirs('public/audio', exist_ok=True)
    
    # OpenAI TTS API endpoint
    url = "https://api.openai.com/v1/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Use alloy voice which works well with Japanese
    voice = "alloy"  # Good for Japanese pronunciation
    
    durations = []
    
    for slide in script_data['slides']:
        slide_num = slide['slide']
        narration = slide['narration']
        
        print(f"🎤 Generating Japanese audio for slide {slide_num}...")
        
        # Prepare request data
        data = {
            "model": "tts-1-hd",  # High-quality model
            "input": narration,
            "voice": voice,
            "response_format": "mp3",  # MP3 format for better web compatibility
            "speed": 0.85  # Slightly slower for Japanese clarity
        }
        
        try:
            # Make API request
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            # Save audio file
            output_file = f"public/audio/earnings-slide-{slide_num}-narration.mp3"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Generated: {output_file}")
            
            # Brief pause to respect rate limits
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error generating audio for slide {slide_num}: {e}")
            if hasattr(e.response, 'text'):
                print(f"   Response: {e.response.text}")
    
    # Get durations of generated files
    print("\\n📊 Audio file durations:")
    total_duration = 0
    for slide in script_data['slides']:
        slide_num = slide['slide']
        audio_file = f"public/audio/earnings-slide-{slide_num}-narration.mp3"
        
        if os.path.exists(audio_file):
            try:
                import subprocess
                cmd = [
                    'ffprobe', '-v', 'quiet', 
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    audio_file
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                duration = float(result.stdout.strip())
                durations.append(duration)
                total_duration += duration
                print(f"  Slide {slide_num}: {duration:.2f}s")
            except (subprocess.CalledProcessError, ValueError) as e:
                print(f"  Slide {slide_num}: Could not determine duration ({e})")
                durations.append(10.0)  # Default fallback for Japanese (longer)
        else:
            durations.append(10.0)  # Default fallback
    
    print(f"\\n🎯 Total audio duration: {total_duration:.2f}s")
    print(f"📺 Recommended video duration: {total_duration + 5:.2f}s (with padding)")
    
    # Update the narration script with durations
    for i, slide in enumerate(script_data['slides']):
        if i < len(durations):
            slide['audio_duration'] = durations[i]
            # Add 1 second padding for slide transitions
            slide['recommended_duration'] = int((durations[i] + 1) * 1000)  # in milliseconds
    
    # Save updated script
    with open('src/earnings-trade-narration-with-durations.json', 'w', encoding='utf-8') as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)
    
    print("\\n✨ Japanese TTS generation complete!")
    print("📝 Updated script with durations saved as 'src/earnings-trade-narration-with-durations.json'")
    print("\\n💡 Next steps:")
    print("1. Update Remotion component to use proper timing")
    print("2. Add component to Root.tsx")
    print("3. Render video with Japanese narration")

if __name__ == "__main__":
    generate_japanese_tts()