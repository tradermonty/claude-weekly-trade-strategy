#!/usr/bin/env python3
"""
Generate natural-sounding audio using OpenAI TTS API
"""
import os
from openai import OpenAI
from pathlib import Path

# Initialize OpenAI client
client = OpenAI()

# Narration texts for each slide
narration_texts = {
    "slide1": """Welcome to our Food and Beverage Sales Briefing for April through August twenty twenty-five. This strategic review covers our results and forward actions for executive leadership.""",

    "slide2": """Why this matters: We've achieved three point five percent revenue growth and four point eight percent unit growth versus April. However, this growth is masking some hidden weaknesses in our Appetizer and ICEE lines that require immediate attention. We're in a critical decision window for fall promotions.""",

    "slide3": """Our financial performance shows strong momentum. Revenue grew from two point one nine six million in April to two point two seven two million in August. We've successfully regained momentum after the May dip, though we did see some unit softness in August compared to July.""",

    "slide4": """Category performance reveals clear winners and concerns. Our top performers include Dessert with eleven point six percent growth, Japanese cuisine up eight point eight percent, and ICEE with nine percent growth. However, we have concerns about Appetizer softness, down zero point six percent despite holding thirty-two point six percent market share. Pizza remains solid with three point five percent growth.""",

    "slide5": """Four standout performers deserve doubled investment. ICEE Float surged fifty-six percent - we need expanded marketing and capacity. Chicken Sandwich Combos grew thirty-two to fifty-one percent with maintained pricing. Cheese Fries Upsize jumped forty-four to forty-seven percent - perfect for digital menu promotion. And JP Chashu Bowl gained thirty-nine percent, validating our premium positioning.""",

    "slide6": """Three areas demand immediate stabilization. Classic ICEE flavors dropped twenty-two to thirty-seven percent - we need fresh flavor rotation. Wing Platter fell twenty-eight percent - time to assess portion value. And Extra Beef Patty declined twenty-two percent - our upsell scripts need revision.""",

    "slide7": """We've identified critical operational red flags. Several key items showed zero sales months, likely due to POS toggles or inventory lockouts. We're implementing weekly zero-sales alerts with mandatory twenty-four hour follow-up to prevent future revenue leakage.""",

    "slide8": """Our thirty-day action plan focuses on five priorities. First, protect our core with an Appetizer save plan. Second, fuel our winners by allocating resources to Dessert, Japanese, and ICEE Float. Third, fix availability through automated alerts. Fourth, optimize pricing with a cross-functional council. And fifth, automate our reporting for consistent leadership updates. Thank you for your attention."""
}

def generate_audio_files():
    """Generate natural audio files using OpenAI TTS"""
    audio_dir = Path("public/audio")
    audio_dir.mkdir(exist_ok=True)

    # Available voices: alloy, echo, fable, onyx, nova, shimmer
    # "nova" is particularly good for professional presentations
    voice = "nova"

    for slide_id, text in narration_texts.items():
        print(f"Generating audio for {slide_id}...")

        try:
            response = client.audio.speech.create(
                model="tts-1-hd",  # High quality model
                voice=voice,
                input=text,
                speed=0.95  # Slightly slower for clarity
            )

            # Save as MP3 first (OpenAI default format)
            mp3_path = audio_dir / f"{slide_id}_natural.mp3"
            response.stream_to_file(mp3_path)
            print(f"Generated: {mp3_path}")

        except Exception as e:
            print(f"Error generating {slide_id}: {e}")

    print("Audio generation complete!")
    print("\nGenerated files:")
    for file in audio_dir.glob("*_natural.mp3"):
        print(f"  {file}")

if __name__ == "__main__":
    generate_audio_files()