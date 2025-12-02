import {Composition} from 'remotion';
import {AVGOSlides} from './AVGOSlides';
import {IOTSlides} from './IOTSlides';
import {AfterMarketSlides} from './AfterMarketSlides';
import {AfterMarketSlidesWithNarration} from './AfterMarketSlidesWithNarration';
import {AfterMarketSlidesOptimized} from './AfterMarketSlidesOptimized';
import {AfterMarketSlidesSquare} from './AfterMarketSlidesSquare';
import {EarningsTradeSlides} from './EarningsTradeSlides';
import {EarningsTradeSquare} from './EarningsTradeSquare';
import {EarningsTradeEnglish} from './EarningsTradeEnglish';
import {EarningsTradeEnglishSept5} from './EarningsTradeEnglishSept5';
import {AfterMarketMobile} from './AfterMarketMobile';
import {AfterMarketSept5Square} from './AfterMarketSept5Square';
import {MarketAnalysisSept21} from './MarketAnalysisSept21';
import {FBSalesBriefing} from './FBSalesBriefing';
import {FBSalesBriefingWithNarration} from './FBSalesBriefingWithNarration';
import {USStockStrategy20250922} from './USStockStrategy20250922';
import {USStockStrategyImproved} from './USStockStrategyImproved';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="AVGOSlides"
				component={AVGOSlides}
				durationInFrames={720} // 24 seconds at 30fps
				fps={30}
				width={1080}
				height={1920}
			/>
			<Composition
				id="IOTSlides"
				component={IOTSlides}
				durationInFrames={720} // 24 seconds at 30fps
				fps={30}
				width={1080}
				height={1920}
			/>
			<Composition
				id="AfterMarketSlides"
				component={AfterMarketSlides}
				durationInFrames={720} // 24 seconds at 30fps (6 slides x 4 seconds each)
				fps={30}
				width={1080}
				height={1920}
			/>
			<Composition
				id="AfterMarketSlidesWithNarration"
				component={AfterMarketSlidesWithNarration}
				durationInFrames={720} // 24 seconds at 30fps (6 slides x 4 seconds each)
				fps={30}
				width={1080}
				height={1920}
			/>
			<Composition
				id="AfterMarketSlidesOptimized"
				component={AfterMarketSlidesOptimized}
				durationInFrames={2093} // ~69.8 seconds at 30fps (optimized for audio length)
				fps={30}
				width={1080}
				height={1920}
			/>
			<Composition
				id="AfterMarketSlidesSquare"
				component={AfterMarketSlidesSquare}
				durationInFrames={2093} // ~69.8 seconds at 30fps (optimized for audio length)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="EarningsTradeSlides"
				component={EarningsTradeSlides}
				durationInFrames={3375} // ~112.5 seconds at 30fps (optimized for Japanese audio)
				fps={30}
				width={1080}
				height={1920}
			/>
			<Composition
				id="EarningsTradeSquare"
				component={EarningsTradeSquare}
				durationInFrames={3375} // ~112.5 seconds at 30fps (optimized for Japanese audio)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="EarningsTradeEnglish"
				component={EarningsTradeEnglish}
				durationInFrames={600} // 20 seconds at 30fps (5 slides x 4 seconds each)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="EarningsTradeEnglishSept5"
				component={EarningsTradeEnglishSept5}
				durationInFrames={1080} // 36 seconds at 30fps (8 slides with varying durations)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="AfterMarketMobile"
				component={AfterMarketMobile}
				durationInFrames={1020} // 34 seconds at 30fps (6 slides with smooth transitions)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="AfterMarketSept5Square"
				component={AfterMarketSept5Square}
				durationInFrames={1140} // 38 seconds at 30fps (6 slides optimized for social media)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="MarketAnalysisSept21"
				component={MarketAnalysisSept21}
				durationInFrames={1080} // 36 seconds at 30fps (6 slides with 6 seconds each for readability)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="FBSalesBriefing"
				component={FBSalesBriefing}
				durationInFrames={2460} // 82 seconds at 30fps (8 slides without extra black frames)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="FBSalesBriefingWithNarration"
				component={FBSalesBriefingWithNarration}
				durationInFrames={4980} // 166 seconds at 30fps (8 slides with OpenAI TTS audio)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="USStockStrategy20250922"
				component={USStockStrategy20250922}
				durationInFrames={11670} // 389 seconds at 30fps (8 slides with Japanese TTS audio)
				fps={30}
				width={1080}
				height={1080}
			/>
			<Composition
				id="USStockStrategyImproved"
				component={USStockStrategyImproved}
				durationInFrames={11670} // 389 seconds at 30fps (8 slides with improved contrast)
				fps={30}
				width={1080}
				height={1080}
			/>
		</>
	);
};