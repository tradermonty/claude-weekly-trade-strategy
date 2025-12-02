#!/usr/bin/env python3
"""
Generate Japanese TTS audio for US Stock Strategy presentation using OpenAI TTS API
"""
import os
from openai import OpenAI
from pathlib import Path

# Initialize OpenAI client
client = OpenAI()

# Japanese narration texts for each slide
narration_texts = {
    "us_strategy_slide1": """
    米国株投資戦略、2025年9月22日週の分析です。今週のテーマは「低ボラティリティと高値更新による選別的リスクオン相場」です。
    S&P500は6,659、NASDAQ100は24,600レベル、10年債利回りは4.12%から4.36%のレンジで推移しています。
    """,

    "us_strategy_slide2": """
    今週のポイントを3つにまとめました。
    第一に、主要指数は週足で続伸しており、S&P500は約6,659、NASDAQ100は約24,600に達していますが、ラッセル2000は2,480の壁を前に足踏み状態です。
    第二に、金利4.13%、VIX15台という低ボラティリティのリスクオン環境は維持されていますが、10年債は4.12%のサポート上で反発気味となっています。
    第三に、コモディティではコントラストが鮮明で、金は3,706ドルで高値更新、ウランETFは週間17%上昇でブレイクアウト、一方で原油は62ドル台で弱含みとなっています。
    """,

    "us_strategy_slide3": """
    市況サマリーから重要レベルを監視します。
    米10年債利回りは週足4.13%で、4.12%が重要サポート、上は4.36%から4.50%が天井帯となります。
    VIXは15.46で低位安定しており、17、20、23をシナリオ切り替えスイッチとして継続監視します。
    Breadthは上昇トレンド比率が30%台半ばに回復しましたが、40%未満のため「広がるラリー未満」で押し目中心が基本戦略となります。
    ゴールドは終値3,706で、3,538ブレイクで青天井状態です。
    """,

    "us_strategy_slide4": """
    セクター・コモディティの1週間パフォーマンスを確認します。
    トップパフォーマーは、通信が3.26%上昇、テクノロジーが2.51%上昇、ウランが12.8%の大幅上昇となりました。
    一方で弱含みセクターは、不動産がマイナス1.50%、生活必需品がマイナス1.41%、原油は62ドル台で軟調です。
    業種上位では原料炭、ウラン、半導体装置、コンピューター・ハードウェア、広告、ソーラーが牽引し、
    メガテックとコミュニケーションが再び主導、景気敏感ではウラン・設備・一部資本財への循環が見られます。
    """,

    "us_strategy_slide5": """
    全体戦略は「やや強気、攻め6対守り4」を据え置きます。
    三点スイッチによる機械的な切り替えを継続し、10年債利回りは4.12%、4.36%、4.50%、
    VIXは17、20、23、Breadthは0.40を重要な閾値として監視します。
    ベースシナリオでは、指数コア70%まで、押し目は8EMAまたは20EMAで拾います。
    リスクオフシナリオでは、ロット半減・新規買い停止、ゴールドやヘッジETFを追加します。
    数値到達で機械的に配分変更を行う規律的なアプローチを維持します。
    """,

    "us_strategy_slide6": """
    アセット別の具体策を週足ベースで説明します。
    S&P500は6,540プラスマイナス40の押し目を待って拾い、6,500割れで撤退、6,700台で段階利確します。
    NASDAQ100は24.1k付近の戻り待ちで分割エントリー、直近安値マイナス1.5%にストップを設定します。
    ラッセル2000は2,480の週足実体ブレイクが条件で、抜けて引けも上なら3分の1ポジション、翌週続伸で追加します。
    ゴールドは3,538上の滞空で強気継続、ヘッジ兼用でポートフォリオの5%を維持します。
    ウランは45プラスマイナス1の押し目のみで新規エントリー、5週線トレーリングで利益を伸ばします。
    原油はWTI65ドル未満は中立から弱気で、65から70ドルへ戻れば短期スイング、72ドル超で強気段階へ移行します。
    """,

    "us_strategy_slide7": """
    セクター配分について、口座の80%を上限として配分します。
    コア指数45%：VOO25%とQQQ20%で、8EMA割れで縮小します。
    テック・AI12%：マイクロソフト、エヌビディア、XLKを押し目限定で保有します。
    素材10%：銅ETFのCOPXやフリーポートマクモランを、銅価格4.708ドル上抜けで増加させます。
    ウラン8%：URAとカメコを押し目限定で保有し、週足陰転で半分利確します。
    金5%：GLD・GDXをVIX20超で増枠します。
    キャッシュ・ヘッジ20%：BIL・SHで、VIX23超または10年債4.50%超でSHを5から10%導入します。
    """,

    "us_strategy_slide8": """
    リスク管理は必ず実装してください。
    基本原則として、1銘柄リスクは0.5%以下、ポートフォリオ全体で1%以内に抑えます。
    VIX23超または10年債4.50%超で新規建て停止とヘッジ導入を行います。
    まとめとして、選別的リスクオン相場が継続しており、テーマはメガテック、金、ウランです。
    戦術的には押し目中心で、追いは浅く抑えます。
    三点スイッチで機械的な配分変更を行い、規律を持った投資を心がけてください。
    本情報は投資判断の参考であり、最終的な売買判断は自己責任でお願いします。
    """
}

def generate_audio_files():
    """Generate Japanese audio files using OpenAI TTS"""
    audio_dir = Path("public/audio")
    audio_dir.mkdir(exist_ok=True)

    # Use "alloy" voice which works well for Japanese
    voice = "alloy"

    for slide_id, text in narration_texts.items():
        print(f"Generating audio for {slide_id}...")

        try:
            response = client.audio.speech.create(
                model="tts-1-hd",  # High quality model
                voice=voice,
                input=text,
                speed=0.9  # Slightly slower for clarity in Japanese
            )

            # Save as MP3 (OpenAI default format)
            mp3_path = audio_dir / f"{slide_id}.mp3"
            response.stream_to_file(mp3_path)
            print(f"Generated: {mp3_path}")

        except Exception as e:
            print(f"Error generating {slide_id}: {e}")

    print("Audio generation complete!")
    print("\nGenerated files:")
    for file in audio_dir.glob("us_strategy_*.mp3"):
        print(f"  {file}")

if __name__ == "__main__":
    generate_audio_files()