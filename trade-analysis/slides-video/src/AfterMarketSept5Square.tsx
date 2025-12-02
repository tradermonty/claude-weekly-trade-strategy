import React from 'react';
import {
	AbsoluteFill,
	interpolate,
	useCurrentFrame,
	useVideoConfig,
	Sequence,
	spring,
} from 'remotion';
import {loadFont} from '@remotion/google-fonts/Inter';

const {fontFamily} = loadFont();

const slideStyle: React.CSSProperties = {
	fontFamily,
	display: 'flex',
	flexDirection: 'column',
	justifyContent: 'center',
	alignItems: 'center',
	color: 'white',
	textAlign: 'center',
	padding: '40px 30px',
	height: '100%',
	boxSizing: 'border-box',
};

// Slide 1: Title and Market Overview
const Slide1: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	
	const titleScale = spring({
		frame,
		fps,
		config: {
			damping: 12,
			stiffness: 200,
		},
	});
	
	const subtitleOpacity = interpolate(frame, [40, 70], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const marketOpacity = interpolate(frame, [70, 100], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '30px', width: '100%'}}>
				{/* Header Section */}
				<div style={{transform: `scale(${titleScale})`, textAlign: 'center'}}>
					<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '10px'}}>🇺🇸 U.S. Market Wrap</div>
					<h1 style={{fontSize: '3.8rem', marginBottom: '15px', fontWeight: 900, lineHeight: 1.1, textShadow: '2px 2px 4px rgba(0,0,0,0.3)'}}>SEPTEMBER 5</h1>
				</div>
				
				<div style={{opacity: subtitleOpacity, textAlign: 'center'}}>
					<h2 style={{fontSize: '2.8rem', fontWeight: 700, marginBottom: '20px', lineHeight: 1.1}}>After-Market Report</h2>
					<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '1.6rem', fontWeight: 600}}>
						📊 Mixed Market Close
					</div>
				</div>
				
				{/* Market Overview */}
				<div style={{
					opacity: marketOpacity, 
					width: '100%',
					maxWidth: '650px'
				}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '2.6rem', marginBottom: '12px', fontWeight: 900, color: '#ff6b6b'}}>
							DIVERGENT MOVES
						</div>
						<div style={{fontSize: '1.8rem', opacity: 0.9, marginBottom: '8px'}}>Small caps +0.50% vs Large caps -0.29%</div>
						<div style={{fontSize: '1.6rem', opacity: 0.7}}>Safe havens shine: TLT +1.52%, GLD +1.33%</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 2: Major ETF Performance 
const Slide2: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const etfOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const insightOpacity = interpolate(frame, [90, 120], [0, 1], {
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
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>📊 ETF PERFORMANCE</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>Major Index Trackers</div>
				</div>

				{/* ETF Grid */}
				<div style={{
					opacity: etfOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '15px',
					width: '100%',
					maxWidth: '700px'
				}}>
					{/* First Row */}
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px'}}>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px 12px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>SPY</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>$647.24</div>
							<div style={{fontSize: '1.6rem', color: '#ff6b6b', fontWeight: 700}}>-0.29%</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px 12px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>QQQ</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>$576.06</div>
							<div style={{fontSize: '1.6rem', color: '#00ff88', fontWeight: 700}}>+0.14%</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px 12px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>DIA</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>$454.99</div>
							<div style={{fontSize: '1.6rem', color: '#ff6b6b', fontWeight: 700}}>-0.45%</div>
						</div>
					</div>

					{/* Second Row */}
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px'}}>
						<div style={{background: 'rgba(255,255,255,0.3)', padding: '20px 12px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '3px solid #00ff88'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>IWM</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>$237.77</div>
							<div style={{fontSize: '1.6rem', color: '#00ff88', fontWeight: 700}}>+0.50%</div>
							<div style={{fontSize: '1.2rem', opacity: 0.9, marginTop: '3px', fontWeight: 600}}>SMALL CAP LEAD</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.3)', padding: '20px 12px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '3px solid #00ff88'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>TLT</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>$88.56</div>
							<div style={{fontSize: '1.6rem', color: '#00ff88', fontWeight: 700}}>+1.52%</div>
							<div style={{fontSize: '1.2rem', opacity: 0.9, marginTop: '3px', fontWeight: 600}}>BONDS RALLY</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.3)', padding: '20px 12px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '3px solid #00ff88'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>GLD</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>$331.05</div>
							<div style={{fontSize: '1.6rem', color: '#00ff88', fontWeight: 700}}>+1.33%</div>
							<div style={{fontSize: '1.2rem', opacity: 0.9, marginTop: '3px', fontWeight: 600}}>GOLD SHINES</div>
						</div>
					</div>

					<div style={{opacity: insightOpacity, background: 'rgba(255,255,255,0.15)', padding: '18px', borderRadius: '18px', backdropFilter: 'blur(10px)', marginTop: '10px'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '5px'}}>💡 Key Insight</div>
						<div style={{fontSize: '1.6rem', opacity: 0.9}}>Risk-off sentiment: Safe havens (bonds, gold) outperform equities</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 3: Volume Surge Winners
const Slide3: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const stocksOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>🔥 VOLUME SURGE</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>Top 5 Movers (97 total)</div>
				</div>

				{/* Stocks List */}
				<div style={{
					opacity: stocksOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '15px',
					width: '100%',
					maxWidth: '700px'
				}}>
					{[
						{symbol: 'KOD', name: 'Kodiak Gas Services', price: '', change: '+23.04%'},
						{symbol: 'ZBIO', name: 'Zappus Bio Tech', price: '', change: '+20.79%'},
						{symbol: 'GWRE', name: 'Guidewire Software', price: '', change: '+20.15%'},
						{symbol: 'KRRO', name: 'Korro Bio', price: '', change: '+18.11%'},
						{symbol: 'EYPT', name: 'EyePoint Pharma', price: '', change: '+17.93%'},
					].map((stock, index) => (
						<div key={index} style={{background: 'rgba(255,255,255,0.25)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
							<div>
								<div style={{fontSize: '2.4rem', fontWeight: 900, marginBottom: '2px'}}>#{index + 1} {stock.symbol}</div>
								<div style={{fontSize: '1.4rem', opacity: 0.8}}>{stock.name}</div>
							</div>
							<div style={{textAlign: 'right'}}>
								<div style={{fontSize: '2rem', color: '#00ff88', fontWeight: 800}}>{stock.change}</div>
							</div>
						</div>
					))}
					
					<div style={{background: 'rgba(255,255,255,0.15)', padding: '18px', borderRadius: '18px', backdropFilter: 'blur(10px)', marginTop: '10px'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '5px'}}>📊 Average Stats</div>
						<div style={{fontSize: '1.6rem', opacity: 0.9}}>+6.9% price move • 2.3x relative volume</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 4: Sector Performance & Market Indices
const Slide4: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const sectorsOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const indicesOpacity = interpolate(frame, [60, 90], [0, 1], {
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
					<h1 style={{fontSize: '2.8rem', marginBottom: '8px', fontWeight: 900}}>🏢 SECTORS & INDICES</h1>
					<div style={{fontSize: '1.5rem', opacity: 0.8}}>Leaders vs Laggards</div>
				</div>

				{/* Sectors List */}
				<div style={{
					opacity: sectorsOpacity,
					width: '100%',
					maxWidth: '700px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '12px', textAlign: 'center'}}>📈 Top Sectors</div>
					<div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
						{[
							{sector: 'Basic Materials', change: '+1.19%'},
							{sector: 'Real Estate', change: '+1.05%'},
							{sector: 'Healthcare', change: '+0.67%'},
							{sector: 'Communication', change: '+0.51%'},
						].map((item, index) => (
							<div key={index} style={{background: 'rgba(255,255,255,0.25)', padding: '12px 18px', borderRadius: '12px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
								<div style={{fontSize: '1.6rem', fontWeight: 600}}>{item.sector}</div>
								<div style={{fontSize: '1.6rem', color: '#00ff88', fontWeight: 800}}>{item.change}</div>
							</div>
						))}
					</div>
				</div>

				{/* Major Indices */}
				<div style={{
					opacity: indicesOpacity,
					width: '100%',
					maxWidth: '700px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '12px', textAlign: 'center'}}>📊 Major Indices</div>
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px'}}>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '15px', borderRadius: '12px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '1.4rem', fontWeight: 600}}>S&P 500</div>
							<div style={{fontSize: '1.8rem', color: '#ff6b6b', fontWeight: 700}}>-19.92 (-0.31%)</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '15px', borderRadius: '12px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
							<div style={{fontSize: '1.4rem', fontWeight: 600}}>Russell 2000</div>
							<div style={{fontSize: '1.8rem', color: '#00ff88', fontWeight: 700}}>+1.18 (+0.50%)</div>
						</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 5: Market Extremes & After-Hours 
const Slide5: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const extremesOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const earningsOpacity = interpolate(frame, [60, 90], [0, 1], {
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
					<h1 style={{fontSize: '2.6rem', marginBottom: '8px', fontWeight: 900}}>🚀 EXTREME MOVES</h1>
					<div style={{fontSize: '1.5rem', opacity: 0.8}}>Biggest Winners & Losers</div>
				</div>

				{/* Extreme Movers */}
				<div style={{
					opacity: extremesOpacity,
					width: '100%',
					maxWidth: '700px'
				}}>
					<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '10px', textAlign: 'center', color: '#00ff88'}}>🎯 TOP GAINERS</div>
					<div style={{display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '20px'}}>
						{[
							{symbol: 'BNDD', name: 'Quadratic Deflation ETF', change: '+707.31%'},
							{symbol: 'CNF', name: 'CNFinance Holdings', change: '+94.17%'},
							{symbol: 'HOUR', name: 'Hour Loop Inc.', change: '+93.12%'},
						].map((stock, index) => (
							<div key={index} style={{background: 'rgba(0,255,136,0.2)', padding: '12px 16px', borderRadius: '12px', backdropFilter: 'blur(10px)', border: '2px solid rgba(0,255,136,0.4)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
								<div style={{fontSize: '1.5rem', fontWeight: 600}}>{stock.symbol}</div>
								<div style={{fontSize: '1.8rem', color: '#00ff88', fontWeight: 900, textShadow: '0 0 1px rgba(0,255,136,0.8), 1px 1px 2px rgba(0,0,0,0.5)', WebkitFontSmoothing: 'antialiased', textRendering: 'optimizeLegibility'}}>{stock.change}</div>
							</div>
						))}
					</div>

					<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '10px', textAlign: 'center', color: '#ff6b6b'}}>📉 TOP LOSERS</div>
					<div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
						{[
							{symbol: 'YAAS', name: 'Youxin Technology', change: '-63.98%'},
							{symbol: 'IBG', name: 'Innovation Beverage Group', change: '-35.02%'},
						].map((stock, index) => (
							<div key={index} style={{background: 'rgba(255,107,107,0.2)', padding: '12px 16px', borderRadius: '12px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,107,107,0.4)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
								<div style={{fontSize: '1.5rem', fontWeight: 600}}>{stock.symbol}</div>
								<div style={{fontSize: '1.6rem', color: '#ff6b6b', fontWeight: 800}}>{stock.change}</div>
							</div>
						))}
					</div>
				</div>

				{/* After-Hours Earnings */}
				<div style={{
					opacity: earningsOpacity,
					background: 'rgba(255,255,255,0.15)', 
					padding: '18px', 
					borderRadius: '18px', 
					backdropFilter: 'blur(10px)',
					width: '100%',
					maxWidth: '700px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 800, marginBottom: '8px', textAlign: 'center'}}>⏰ EARNINGS UPDATE</div>
					<div style={{fontSize: '1.6rem', opacity: 0.9, textAlign: 'center'}}>Limited activity: Only 2 companies reported</div>
					<div style={{fontSize: '1.4rem', opacity: 0.8, textAlign: 'center', marginTop: '5px'}}>PLCE (mixed results) • BASE (positive surprise)</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 6: Key Takeaways
const Slide6: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const takeawaysOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const finalMessageScale = spring({
		frame: frame - 120,
		fps,
		config: {
			damping: 12,
			stiffness: 150,
		},
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
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>🔍 KEY TAKEAWAYS</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8, fontWeight: 600}}>September 5, 2025</div>
				</div>

				{/* Key Points */}
				<div style={{
					opacity: takeawaysOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '12px',
					width: '100%',
					maxWidth: '700px'
				}}>
					{[
						'📊 Mixed performance: Small caps outperform large caps',
						'💰 Safe haven flows: Bonds +1.52%, Gold +1.33%',
						'🔥 Strong volume activity: 97 surge stocks, 881 uptrends',
						'🏢 Materials & Real Estate lead sectors',
						'⚡ Biotech surge led by KOD +23%, GWRE +20%',
						'⏰ Light earnings season: Limited after-hours impact'
					].map((takeaway, index) => (
						<div key={index} style={{background: 'rgba(44,62,80,0.85)', padding: '15px 18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(44,62,80,0.9)'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 600, lineHeight: 1.3, color: '#ffffff', textShadow: '1px 1px 2px rgba(0,0,0,0.7)'}}>{takeaway}</div>
						</div>
					))}
				</div>
				
				<div style={{
					transform: `scale(${finalMessageScale})`,
					background: 'rgba(44,62,80,0.9)', 
					padding: '20px', 
					borderRadius: '20px', 
					backdropFilter: 'blur(10px)', 
					border: '2px solid rgba(44,62,80,1)',
					marginTop: '15px',
					width: '100%',
					maxWidth: '700px'
				}}>
					<div style={{fontSize: '2.2rem', fontWeight: 900, textAlign: 'center', color: '#ffffff', textShadow: '1px 1px 2px rgba(0,0,0,0.7)'}}>📈 WATCH: Sector rotation & safe haven demand</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Main composition optimized for 1:1 square format (1080x1080) - Twitter/X optimized
export const AfterMarketSept5Square: React.FC = () => {
	const {fps} = useVideoConfig();
	
	// Slide durations optimized for social media (shorter, more engaging)
	const slideDurations = [
		Math.ceil(5 * fps),    // Slide 1: 5 seconds - Title & Overview
		Math.ceil(6 * fps),    // Slide 2: 6 seconds - ETF Performance
		Math.ceil(6 * fps),    // Slide 3: 6 seconds - Volume Surge Winners
		Math.ceil(6 * fps),    // Slide 4: 6 seconds - Sectors & Indices  
		Math.ceil(7 * fps),    // Slide 5: 7 seconds - Extreme Moves & Earnings
		Math.ceil(8 * fps),    // Slide 6: 8 seconds - Key Takeaways
	];
	
	let currentFrame = 0;

	return (
		<AbsoluteFill>
			{/* Slide 1: Market Overview */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[0]}>
				<Slide1 />
			</Sequence>
			{currentFrame += slideDurations[0]}

			{/* Slide 2: ETF Performance */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[1]}>
				<Slide2 />
			</Sequence>
			{currentFrame += slideDurations[1]}

			{/* Slide 3: Volume Surge Winners */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[2]}>
				<Slide3 />
			</Sequence>
			{currentFrame += slideDurations[2]}

			{/* Slide 4: Sectors & Indices */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[3]}>
				<Slide4 />
			</Sequence>
			{currentFrame += slideDurations[3]}

			{/* Slide 5: Extreme Moves & Earnings */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[4]}>
				<Slide5 />
			</Sequence>
			{currentFrame += slideDurations[4]}

			{/* Slide 6: Key Takeaways */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[5]}>
				<Slide6 />
			</Sequence>
		</AbsoluteFill>
	);
};