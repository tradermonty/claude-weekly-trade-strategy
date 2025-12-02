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

// Slide 1: Title and Date
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

	const subtitleOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const regimeOpacity = interpolate(frame, [60, 90], [0, 1], {
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
					<div style={{fontSize: '2.2rem', opacity: 0.8, marginBottom: '10px'}}>📊 Market Analysis</div>
					<h1 style={{fontSize: '3.8rem', marginBottom: '15px', fontWeight: 900, lineHeight: 1.1, textShadow: '2px 2px 4px rgba(0,0,0,0.3)'}}>SEPT 21, 2025</h1>
				</div>

				<div style={{opacity: subtitleOpacity, textAlign: 'center'}}>
					<h2 style={{fontSize: '2.6rem', fontWeight: 700, marginBottom: '20px', lineHeight: 1.1}}>Situational Analysis</h2>
					<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600}}>
						🇺🇸 Pre-Market Report
					</div>
				</div>

				{/* Market Regime */}
				<div style={{
					opacity: regimeOpacity,
					width: '100%',
					maxWidth: '650px'
				}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '2.8rem', marginBottom: '12px', fontWeight: 900, color: '#4CAF50'}}>
							MIXED TO POSITIVE
						</div>
						<div style={{fontSize: '1.8rem', opacity: 0.9, marginBottom: '8px'}}>Technology leadership driving growth</div>
						<div style={{fontSize: '1.6rem', opacity: 0.7}}>S&P 500 near historical highs</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 2: Major Indices Performance
const Slide2: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const indicesOpacity = interpolate(frame, [30, 60], [0, 1], {
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
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>📈 MAJOR INDICES</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>Market Performance</div>
				</div>

				{/* Indices Grid */}
				<div style={{
					opacity: indicesOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '15px',
					width: '100%',
					maxWidth: '700px'
				}}>
					{/* S&P 500 and NASDAQ */}
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px'}}>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px 15px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(76,175,80,0.6)'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>S&P 500</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>6,664.36</div>
							<div style={{fontSize: '1.8rem', color: '#4CAF50', fontWeight: 700}}>+32.4 (+0.49%)</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px 15px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(76,175,80,0.6)'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>NASDAQ</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>22,631.48</div>
							<div style={{fontSize: '1.8rem', color: '#4CAF50', fontWeight: 700}}>+160.75 (+0.72%)</div>
						</div>
					</div>

					{/* Dow Jones and Russell 2000 */}
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px'}}>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px 15px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(76,175,80,0.6)'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>DOW</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>46,315.27</div>
							<div style={{fontSize: '1.8rem', color: '#4CAF50', fontWeight: 700}}>+172.85 (+0.37%)</div>
						</div>
						<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px 15px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,107,107,0.6)'}}>
							<div style={{fontSize: '2.2rem', fontWeight: 900, marginBottom: '8px'}}>RUSSELL</div>
							<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>2,448.77</div>
							<div style={{fontSize: '1.8rem', color: '#ff6b6b', fontWeight: 700}}>-18.93 (-0.77%)</div>
						</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.15)', padding: '18px', borderRadius: '18px', backdropFilter: 'blur(10px)', marginTop: '10px'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '5px'}}>💡 Key Insight</div>
						<div style={{fontSize: '1.6rem', opacity: 0.9}}>Large-cap strength vs small-cap weakness</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 3: Sector Performance
const Slide3: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const sectorsOpacity = interpolate(frame, [30, 60], [0, 1], {
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
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>🏢 SECTOR HIGHLIGHTS</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>Leaders & Laggards</div>
				</div>

				{/* Sectors List */}
				<div style={{
					opacity: sectorsOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '12px',
					width: '100%',
					maxWidth: '700px'
				}}>
					<div style={{fontSize: '2rem', fontWeight: 700, marginBottom: '8px', textAlign: 'center', color: '#4CAF50'}}>🚀 TOP PERFORMERS</div>
					{[
						{sector: 'Technology', change: '+0.88%', highlight: true},
						{sector: 'Utilities', change: '+0.84%', highlight: true},
						{sector: 'Communication Services', change: '+0.48%', highlight: false},
					].map((item, index) => (
						<div key={index} style={{
							background: item.highlight ? 'rgba(76,175,80,0.3)' : 'rgba(255,255,255,0.25)',
							padding: '18px 20px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: item.highlight ? '3px solid #4CAF50' : '2px solid rgba(255,255,255,0.3)',
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center'
						}}>
							<div style={{fontSize: '1.8rem', fontWeight: 700}}>{item.sector}</div>
							<div style={{fontSize: '2rem', color: '#4CAF50', fontWeight: 800}}>{item.change}</div>
						</div>
					))}

					<div style={{fontSize: '2rem', fontWeight: 700, marginTop: '10px', marginBottom: '8px', textAlign: 'center', color: '#ff6b6b'}}>📉 LAGGARDS</div>
					{[
						{sector: 'Energy', change: '-1.23%'},
						{sector: 'Real Estate', change: '-0.64%'},
					].map((item, index) => (
						<div key={index} style={{background: 'rgba(255,107,107,0.25)', padding: '18px 20px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,107,107,0.4)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
							<div style={{fontSize: '1.8rem', fontWeight: 700}}>{item.sector}</div>
							<div style={{fontSize: '2rem', color: '#ff6b6b', fontWeight: 800}}>{item.change}</div>
						</div>
					))}
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 4: Key Market Metrics
const Slide4: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const metricsOpacity = interpolate(frame, [30, 60], [0, 1], {
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
					<h1 style={{fontSize: '2.8rem', marginBottom: '8px', fontWeight: 900}}>📊 KEY METRICS</h1>
					<div style={{fontSize: '1.5rem', opacity: 0.8}}>Market Activity Overview</div>
				</div>

				{/* Metrics Grid */}
				<div style={{
					opacity: metricsOpacity,
					width: '100%',
					maxWidth: '700px'
				}}>
					{/* Cap Performance */}
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px'}}>
						<div style={{background: 'rgba(76,175,80,0.3)', padding: '20px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '3px solid #4CAF50'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 600, marginBottom: '5px'}}>Mega Cap</div>
							<div style={{fontSize: '2.4rem', color: '#4CAF50', fontWeight: 900, marginBottom: '3px'}}>+0.70%</div>
							<div style={{fontSize: '1.4rem', opacity: 0.9}}>$41.9T Market Cap</div>
						</div>
						<div style={{background: 'rgba(255,107,107,0.3)', padding: '20px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '3px solid #ff6b6b'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 600, marginBottom: '5px'}}>Small Cap</div>
							<div style={{fontSize: '2.4rem', color: '#ff6b6b', fontWeight: 900, marginBottom: '3px'}}>-0.40%</div>
							<div style={{fontSize: '1.4rem', opacity: 0.9}}>$1.5T Market Cap</div>
						</div>
					</div>

					{/* Volume Activity */}
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', marginBottom: '15px'}}>
						<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '10px', textAlign: 'center'}}>🔥 VOLUME SURGE</div>
						<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '1.6rem'}}>
							<div><span style={{color: '#4CAF50', fontWeight: 700}}>137</span> stocks surging</div>
							<div><span style={{color: '#4CAF50', fontWeight: 700}}>880</span> uptrends</div>
						</div>
						<div style={{fontSize: '1.4rem', opacity: 0.9, textAlign: 'center', marginTop: '8px'}}>Average: +6.4% price move • 3.4x volume</div>
					</div>

					{/* Gold Performance */}
					<div style={{background: 'rgba(255,193,7,0.2)', padding: '15px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid #FFC107'}}>
						<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
							<div style={{fontSize: '1.8rem', fontWeight: 700}}>🥇 Gold (GLD)</div>
							<div style={{fontSize: '2rem', color: '#FFC107', fontWeight: 800}}>+1.06%</div>
						</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 5: Strategic Outlook
const Slide5: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const outlookOpacity = interpolate(frame, [30, 60], [0, 1], {
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
					<h1 style={{fontSize: '2.8rem', marginBottom: '8px', fontWeight: 900}}>🎯 STRATEGIC OUTLOOK</h1>
					<div style={{fontSize: '1.5rem', opacity: 0.8}}>Market Positioning</div>
				</div>

				{/* Outlook Points */}
				<div style={{
					opacity: outlookOpacity,
					width: '100%',
					maxWidth: '700px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '15px', textAlign: 'center', color: '#4CAF50'}}>✅ POSITIVE FACTORS</div>
					<div style={{display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px'}}>
						{[
							'Technology leadership continues',
							'Mega-cap providing strong support',
							'Volume surge indicates institutional interest',
							'Constructive sector rotation patterns'
						].map((point, index) => (
							<div key={index} style={{background: 'rgba(76,175,80,0.2)', padding: '15px 18px', borderRadius: '12px', backdropFilter: 'blur(10px)', border: '2px solid rgba(76,175,80,0.4)'}}>
								<div style={{fontSize: '1.6rem', fontWeight: 600, lineHeight: 1.3}}>{point}</div>
							</div>
						))}
					</div>

					<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '15px', textAlign: 'center', color: '#ff6b6b'}}>⚠️ WATCH FACTORS</div>
					<div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
						{[
							'Concentration risk in mega-cap tech',
							'Small-cap underperformance signals',
							'Energy sector weakness'
						].map((point, index) => (
							<div key={index} style={{background: 'rgba(255,107,107,0.2)', padding: '15px 18px', borderRadius: '12px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,107,107,0.4)'}}>
								<div style={{fontSize: '1.6rem', fontWeight: 600, lineHeight: 1.3}}>{point}</div>
							</div>
						))}
					</div>
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
		frame: frame - 90,
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
					<div style={{fontSize: '1.6rem', opacity: 0.8, fontWeight: 600}}>September 21, 2025</div>
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
						'📊 MIXED TO POSITIVE market regime confirmed',
						'🚀 Technology sector leads with +0.88% gains',
						'💪 Mega-cap strength (+0.70%) vs small-cap weakness',
						'🔥 137 volume surge stocks showing momentum',
						'🥇 Safe haven demand: Gold +1.06%, Utilities +0.84%',
						'⚡ Apple & Robinhood standout performers (+3.20%)'
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
					<div style={{fontSize: '2.2rem', fontWeight: 900, textAlign: 'center', color: '#ffffff', textShadow: '1px 1px 2px rgba(0,0,0,0.7)'}}>📈 FOCUS: Quality tech names & sector rotation</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Main composition optimized for 1:1 square format (1080x1080) - Twitter/X optimized
export const MarketAnalysisSept21: React.FC = () => {
	const {fps} = useVideoConfig();

	// Slide durations optimized for readability (longer for better comprehension)
	// Total duration: ~36 seconds
	const slideDurations = [
		Math.ceil(6 * fps),    // Slide 1: 6 seconds - Title & Regime
		Math.ceil(6 * fps),    // Slide 2: 6 seconds - Major Indices
		Math.ceil(6 * fps),    // Slide 3: 6 seconds - Sector Performance
		Math.ceil(6 * fps),    // Slide 4: 6 seconds - Key Metrics
		Math.ceil(6 * fps),    // Slide 5: 6 seconds - Strategic Outlook
		Math.ceil(6 * fps),    // Slide 6: 6 seconds - Key Takeaways
	];

	let currentFrame = 0;

	return (
		<AbsoluteFill>
			{/* Slide 1: Title & Market Regime */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[0]}>
				<Slide1 />
			</Sequence>
			{currentFrame += slideDurations[0]}

			{/* Slide 2: Major Indices Performance */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[1]}>
				<Slide2 />
			</Sequence>
			{currentFrame += slideDurations[1]}

			{/* Slide 3: Sector Performance */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[2]}>
				<Slide3 />
			</Sequence>
			{currentFrame += slideDurations[2]}

			{/* Slide 4: Key Market Metrics */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[3]}>
				<Slide4 />
			</Sequence>
			{currentFrame += slideDurations[3]}

			{/* Slide 5: Strategic Outlook */}
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