#!/bin/bash

# Generate natural-sounding audio using macOS Samantha voice
# More natural speaking rate and intonation

cd "$(dirname "$0")"

# Create audio directory if it doesn't exist
mkdir -p public/audio

# Define narration texts
declare -A narration_texts=(
    ["slide1"]="Welcome to our Food and Beverage Sales Briefing for April through August twenty twenty-five. This strategic review covers our results and forward actions for executive leadership."

    ["slide2"]="Why this matters: We've achieved three point five percent revenue growth and four point eight percent unit growth versus April. However, this growth is masking some hidden weaknesses in our Appetizer and ICEE lines that require immediate attention. We're in a critical decision window for fall promotions."

    ["slide3"]="Our financial performance shows strong momentum. Revenue grew from two point one nine six million in April to two point two seven two million in August. We've successfully regained momentum after the May dip, though we did see some unit softness in August compared to July."

    ["slide4"]="Category performance reveals clear winners and concerns. Our top performers include Dessert with eleven point six percent growth, Japanese cuisine up eight point eight percent, and ICEE with nine percent growth. However, we have concerns about Appetizer softness, down zero point six percent despite holding thirty-two point six percent market share. Pizza remains solid with three point five percent growth."

    ["slide5"]="Four standout performers deserve doubled investment. ICEE Float surged fifty-six percent - we need expanded marketing and capacity. Chicken Sandwich Combos grew thirty-two to fifty-one percent with maintained pricing. Cheese Fries Upsize jumped forty-four to forty-seven percent - perfect for digital menu promotion. And JP Chashu Bowl gained thirty-nine percent, validating our premium positioning."

    ["slide6"]="Three areas demand immediate stabilization. Classic ICEE flavors dropped twenty-two to thirty-seven percent - we need fresh flavor rotation. Wing Platter fell twenty-eight percent - time to assess portion value. And Extra Beef Patty declined twenty-two percent - our upsell scripts need revision."

    ["slide7"]="We've identified critical operational red flags. Several key items showed zero sales months, likely due to POS toggles or inventory lockouts. We're implementing weekly zero-sales alerts with mandatory twenty-four hour follow-up to prevent future revenue leakage."

    ["slide8"]="Our thirty-day action plan focuses on five priorities. First, protect our core with an Appetizer save plan. Second, fuel our winners by allocating resources to Dessert, Japanese, and ICEE Float. Third, fix availability through automated alerts. Fourth, optimize pricing with a cross-functional council. And fifth, automate our reporting for consistent leadership updates. Thank you for your attention."
)

echo "Generating natural audio files with Samantha voice..."

for slide in slide1 slide2 slide3 slide4 slide5 slide6 slide7 slide8; do
    echo "Generating audio for $slide..."

    # Use Samantha voice with:
    # -r 180: Slightly slower rate for clarity (default 175-200)
    # Better pronunciation and natural pauses
    echo "${narration_texts[$slide]}" | say -v "Samantha" -r 180 -o "public/audio/${slide}_natural.aiff"

    # Convert to WAV for better compatibility
    ffmpeg -i "public/audio/${slide}_natural.aiff" -acodec pcm_s16le "public/audio/${slide}_natural.wav" -y -loglevel quiet

    echo "Generated: public/audio/${slide}_natural.wav"
done

echo ""
echo "Audio generation complete!"
echo "Generated files:"
ls -la public/audio/*_natural.wav

echo ""
echo "Checking durations:"
for file in public/audio/*_natural.wav; do
    duration=$(afinfo "$file" | grep "estimated duration" | awk '{print $3}')
    echo "$(basename "$file"): ${duration} seconds"
done