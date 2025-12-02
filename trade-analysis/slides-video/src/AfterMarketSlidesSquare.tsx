import React from 'react';
import {
	AbsoluteFill,
	interpolate,
	useCurrentFrame,
	useVideoConfig,
	Sequence,
	Audio,
	staticFile,
} from 'remotion';
import {loadFont} from '@remotion/google-fonts/Inter';

const {fontFamily} = loadFont();

const slideStyle: React.CSSProperties = {
	fontFamily,
	display: 'flex',
	flexDirection: 'column',
	justifyContent: 'center', // Changed from 'space-between' to center content
	alignItems: 'center',
	color: 'white',
	textAlign: 'center',
	padding: '40px 30px', // Adjusted padding for square format
	height: '100%',
	boxSizing: 'border-box',
};

// Slide 1: Title and Market Overview
const Slide1: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const marketOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const statsOpacity = interpolate(frame, [60, 90], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '30px', width: '100%'}}>
				{/* Header Section */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<div style={{fontSize: '1.6rem', opacity: 0.8, marginBottom: '10px'}}>🇺🇸 U.S. Market Wrap</div>
					<h1 style={{fontSize: '3.2rem', marginBottom: '10px', fontWeight: 800, lineHeight: 1.1}}>SEPTEMBER 4</h1>
					<h2 style={{fontSize: '2.4rem', fontWeight: 600, marginBottom: '15px', lineHeight: 1.1}}>After-Market Report</h2>
					<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '8px 16px', borderRadius: '20px', fontSize: '1.4rem', fontWeight: 600}}>
						📊 Final Trading Data
					</div>
				</div>
				
				{/* Market Overview */}
				<div style={{
					opacity: marketOpacity, 
					width: '100%',
					maxWidth: '600px'
				}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '20px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '2.2rem', marginBottom: '8px', fontWeight: 800, color: '#00ff88'}}>
							BROAD RALLY
						</div>
						<div style={{fontSize: '1.6rem', opacity: 0.9, marginBottom: '5px'}}>All major sectors positive</div>
						<div style={{fontSize: '1.4rem', opacity: 0.7}}>Risk-on sentiment dominates</div>
					</div>
				</div>

				{/* Quick Stats */}
				<div style={{
					opacity: statsOpacity, 
					display: 'flex',
					gap: '20px',
					width: '100%',
					justifyContent: 'center'
				}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '15px', borderRadius: '12px', backdropFilter: 'blur(10px)', flex: 1, maxWidth: '120px'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 800, color: '#00ff88'}}>81</div>
						<div style={{fontSize: '1.2rem', opacity: 0.9}}>Volume Surge</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '15px', borderRadius: '12px', backdropFilter: 'blur(10px)', flex: 1, maxWidth: '120px'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 800, color: '#00ff88'}}>887</div>
						<div style={{fontSize: '1.2rem', opacity: 0.9}}>Up-trend</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 2: Major ETF Performance
const Slide2: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const etfOpacity = interpolate(frame, [20, 50], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '2.6rem', marginBottom: '8px', fontWeight: 800}}>📊 ETF PERFORMANCE</h1>
					<div style={{fontSize: '1.4rem', opacity: 0.8}}>Major Index Trackers</div>
				</div>

				{/* ETF Grid */}
				<div style={{
					opacity: etfOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '15px',
					width: '100%',
					maxWidth: '650px'
				}}>
					{/* First Row */}
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px'}}>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '5px'}}>SPY</div>
							<div style={{fontSize: '1.6rem', marginBottom: '5px'}}>$649.12</div>
							<div style={{fontSize: '1.4rem', color: '#00ff88', fontWeight: 600}}>+0.84%</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '5px'}}>QQQ</div>
							<div style={{fontSize: '1.6rem', marginBottom: '5px'}}>$575.23</div>
							<div style={{fontSize: '1.4rem', color: '#00ff88', fontWeight: 600}}>+0.91%</div>
						</div>
					</div>

					{/* Second Row */}
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px'}}>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '5px'}}>IWM</div>
							<div style={{fontSize: '1.6rem', marginBottom: '5px'}}>$236.59</div>
							<div style={{fontSize: '1.4rem', color: '#00ff88', fontWeight: 600}}>+1.25%</div>
							<div style={{fontSize: '1.1rem', opacity: 0.8, marginTop: '3px'}}>Small Caps Lead</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '5px'}}>DIA</div>
							<div style={{fontSize: '1.6rem', marginBottom: '5px'}}>$457.05</div>
							<div style={{fontSize: '1.4rem', color: '#00ff88', fontWeight: 600}}>+0.84%</div>
						</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.15)', padding: '15px', borderRadius: '15px', backdropFilter: 'blur(10px)', marginTop: '10px'}}>
						<div style={{fontSize: '1.4rem', fontWeight: 600, marginBottom: '5px'}}>💡 Key Insight</div>
						<div style={{fontSize: '1.3rem', opacity: 0.9}}>Small caps (IWM) outperforming indicates strong risk appetite</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 3: Volume Surge Winners
const Slide3: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const stocksOpacity = interpolate(frame, [20, 50], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '2.6rem', marginBottom: '8px', fontWeight: 800}}>🔥 VOLUME SURGE</h1>
					<div style={{fontSize: '1.4rem', opacity: 0.8}}>Top Movers Today</div>
				</div>

				{/* Stocks List */}
				<div style={{
					opacity: stocksOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '12px',
					width: '100%',
					maxWidth: '650px'
				}}>
					<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
						<div>
							<div style={{fontSize: '2rem', fontWeight: 800}}>AEO</div>
							<div style={{fontSize: '1.3rem', opacity: 0.8}}>105.2M vol</div>
						</div>
						<div style={{textAlign: 'right'}}>
							<div style={{fontSize: '1.8rem', marginBottom: '3px'}}>$18.79</div>
							<div style={{fontSize: '1.6rem', color: '#00ff88', fontWeight: 700}}>+37.93%</div>
						</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
						<div>
							<div style={{fontSize: '2rem', fontWeight: 800}}>NEGG</div>
							<div style={{fontSize: '1.3rem', opacity: 0.8}}>4.5M vol</div>
						</div>
						<div style={{textAlign: 'right'}}>
							<div style={{fontSize: '1.8rem', marginBottom: '3px'}}>$40.25</div>
							<div style={{fontSize: '1.6rem', color: '#00ff88', fontWeight: 700}}>+29.93%</div>
						</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
						<div>
							<div style={{fontSize: '2rem', fontWeight: 800}}>CIEN</div>
							<div style={{fontSize: '1.3rem', opacity: 0.8}}>11.3M vol</div>
						</div>
						<div style={{textAlign: 'right'}}>
							<div style={{fontSize: '1.8rem', marginBottom: '3px'}}>$116.92</div>
							<div style={{fontSize: '1.6rem', color: '#00ff88', fontWeight: 700}}>+23.29%</div>
						</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.15)', padding: '15px', borderRadius: '15px', backdropFilter: 'blur(10px)', marginTop: '10px'}}>
						<div style={{fontSize: '1.6rem', fontWeight: 600, opacity: 0.9}}>Average: +6.3% with 2.4x relative volume</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 4: Sector Performance
const Slide4: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const sectorsOpacity = interpolate(frame, [20, 50], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '2.6rem', marginBottom: '8px', fontWeight: 800}}>🏢 SECTOR ROTATION</h1>
					<div style={{fontSize: '1.4rem', opacity: 0.8}}>All Sectors Positive</div>
				</div>

				{/* Sectors List */}
				<div style={{
					opacity: sectorsOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '10px',
					width: '100%',
					maxWidth: '650px'
				}}>
					{[
						{sector: 'Consumer Discretionary', change: '+1.85%'},
						{sector: 'Technology', change: '+1.42%'},
						{sector: 'Communication Services', change: '+1.28%'},
						{sector: 'Financials', change: '+1.15%'},
						{sector: 'Industrials', change: '+0.94%'},
						{sector: 'Materials', change: '+0.67%'},
					].map((item, index) => (
						<div key={index} style={{background: 'rgba(255,255,255,0.25)', padding: '12px', borderRadius: '12px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
							<div style={{fontSize: '1.5rem', fontWeight: 600}}>{item.sector}</div>
							<div style={{fontSize: '1.5rem', color: '#00ff88', fontWeight: 700}}>{item.change}</div>
						</div>
					))}
					
					<div style={{background: 'rgba(255,255,255,0.15)', padding: '12px', borderRadius: '12px', backdropFilter: 'blur(10px)', marginTop: '10px'}}>
						<div style={{fontSize: '1.5rem', fontWeight: 600, opacity: 0.9}}>🎯 Broad-based strength across all sectors</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 5: After-Hours Earnings
const Slide5: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const earningsOpacity = interpolate(frame, [20, 50], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '2.4rem', marginBottom: '8px', fontWeight: 800}}>⏰ AFTER-HOURS</h1>
					<div style={{fontSize: '1.4rem', opacity: 0.8}}>Earnings Winners</div>
				</div>

				{/* Earnings Winners */}
				<div style={{
					opacity: earningsOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '12px',
					width: '100%',
					maxWidth: '650px'
				}}>
					<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
							<div style={{fontSize: '2rem', fontWeight: 800}}>BRZE</div>
							<div style={{fontSize: '1.8rem', color: '#00ff88', fontWeight: 700}}>+15.40%</div>
						</div>
						<div style={{fontSize: '1.3rem', opacity: 0.8}}>EPS Beat: +52.51% | Revenue Beat: +2.17%</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
							<div style={{fontSize: '2rem', fontWeight: 800}}>GWRE</div>
							<div style={{fontSize: '1.8rem', color: '#00ff88', fontWeight: 700}}>+14.56%</div>
						</div>
						<div style={{fontSize: '1.3rem', opacity: 0.8}}>EPS Beat: +90.35% | Revenue Beat: +2.51%</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.25)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
							<div style={{fontSize: '2rem', fontWeight: 800}}>IOT</div>
							<div style={{fontSize: '1.8rem', color: '#00ff88', fontWeight: 700}}>+8.73%</div>
						</div>
						<div style={{fontSize: '1.3rem', opacity: 0.8}}>EPS Beat: +89.98% | Revenue Beat: +4.40%</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.15)', padding: '15px', borderRadius: '15px', backdropFilter: 'blur(10px)', marginTop: '10px'}}>
						<div style={{fontSize: '1.6rem', fontWeight: 600, opacity: 0.9}}>🎯 Tech sector dominating earnings</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 6: Key Takeaways
const Slide6: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const takeawaysOpacity = interpolate(frame, [20, 50], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
			color: '#2c3e50',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '2.6rem', marginBottom: '8px', fontWeight: 800}}>🔍 KEY TAKEAWAYS</h1>
					<div style={{fontSize: '1.4rem', opacity: 0.8}}>September 4, 2025</div>
				</div>

				{/* Key Points */}
				<div style={{
					opacity: takeawaysOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '12px',
					width: '100%',
					maxWidth: '650px'
				}}>
					{[
						'📈 Broad market rally with all sectors positive',
						'🚀 Small caps (IWM) outperformed large caps',
						'🔥 High-quality earnings beats driving after-hours action',
						'💪 Strong risk-on sentiment across the market',
						'🎯 Tech sector leading both regular and after-hours sessions'
					].map((takeaway, index) => (
						<div key={index} style={{background: 'rgba(255,255,255,0.4)', padding: '15px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.5)'}}>
							<div style={{fontSize: '1.4rem', fontWeight: 600}}>{takeaway}</div>
						</div>
					))}
					
					<div style={{background: 'rgba(44,62,80,0.1)', padding: '15px', borderRadius: '15px', backdropFilter: 'blur(10px)', marginTop: '15px'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700}}>✨ Tomorrow's Focus: Maintain momentum</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Main composition optimized for 1:1 square format (1080x1080)
export const AfterMarketSlidesSquare: React.FC = () => {
	const {fps} = useVideoConfig();
	
	// Slide durations based on actual audio length + padding (in frames)
	const slideDurations = [
		Math.ceil((10.968 + 1) * fps), // Slide 1: ~359 frames (11.97s)
		Math.ceil((10.632 + 1) * fps), // Slide 2: ~349 frames (11.63s)  
		Math.ceil((10.272 + 1) * fps), // Slide 3: ~338 frames (11.27s)
		Math.ceil((10.416 + 1) * fps), // Slide 4: ~342 frames (11.42s)
		Math.ceil((10.848 + 1) * fps), // Slide 5: ~355 frames (11.85s)
		Math.ceil((10.656 + 4) * fps), // Slide 6: ~440 frames (14.67s) - Extended for better visibility
	];
	
	let currentFrame = 0;

	return (
		<AbsoluteFill>
			{/* Slide 1 */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[0]}>
				<Slide1 />
				<Audio src={staticFile('audio/slide-1-narration.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[0]}

			{/* Slide 2 */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[1]}>
				<Slide2 />
				<Audio src={staticFile('audio/slide-2-narration.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[1]}

			{/* Slide 3 */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[2]}>
				<Slide3 />
				<Audio src={staticFile('audio/slide-3-narration.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[2]}

			{/* Slide 4 */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[3]}>
				<Slide4 />
				<Audio src={staticFile('audio/slide-4-narration.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[3]}

			{/* Slide 5 */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[4]}>
				<Slide5 />
				<Audio src={staticFile('audio/slide-5-narration.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[4]}

			{/* Slide 6 */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[5]}>
				<Slide6 />
				<Audio src={staticFile('audio/slide-6-narration.mp3')} />
			</Sequence>
		</AbsoluteFill>
	);
};