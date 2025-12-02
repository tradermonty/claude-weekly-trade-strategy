import React from 'react';
import {
	AbsoluteFill,
	interpolate,
	useCurrentFrame,
	useVideoConfig,
	Sequence,
} from 'remotion';
import {loadFont} from '@remotion/google-fonts/Inter';

const {fontFamily} = loadFont();

const slideStyle: React.CSSProperties = {
	fontFamily,
	display: 'flex',
	flexDirection: 'column',
	justifyContent: 'space-between',
	alignItems: 'center',
	color: 'white',
	textAlign: 'center',
	padding: '30px 25px',
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
			{/* Header Section */}
			<div style={{opacity: titleOpacity, textAlign: 'center', marginTop: '20px'}}>
				<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '15px'}}>🇺🇸 U.S. Market Wrap</div>
				<h1 style={{fontSize: '5rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>SEPTEMBER 4</h1>
				<h2 style={{fontSize: '3.5rem', fontWeight: 600, marginBottom: '20px', lineHeight: 1.1}}>After-Market Report</h2>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600}}>
					📊 Final Trading Data
				</div>
			</div>
			
			{/* Market Overview */}
			<div style={{
				opacity: marketOpacity, 
				display: 'flex',
				flexDirection: 'column',
				gap: '20px', 
				width: '100%', 
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '3rem', marginBottom: '12px', fontWeight: 800, color: '#00ff88'}}>
						BROAD RALLY
					</div>
					<div style={{fontSize: '2rem', opacity: 0.9}}>All major sectors positive</div>
					<div style={{fontSize: '2.2rem', opacity: 0.7}}>Risk-on sentiment dominates</div>
				</div>
			</div>

			{/* Quick Stats */}
			<div style={{
				opacity: statsOpacity, 
				display: 'grid', 
				gridTemplateColumns: '1fr 1fr', 
				gap: '15px', 
				width: '100%',
				marginBottom: '20px'
			}}>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '20px', borderRadius: '15px', backdropFilter: 'blur(10px)'}}>
					<div style={{fontSize: '2.5rem', fontWeight: 800, color: '#00ff88'}}>81</div>
					<div style={{fontSize: '2rem', opacity: 0.9}}>Volume Surge</div>
				</div>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '20px', borderRadius: '15px', backdropFilter: 'blur(10px)'}}>
					<div style={{fontSize: '2.5rem', fontWeight: 800, color: '#00ff88'}}>887</div>
					<div style={{fontSize: '2rem', opacity: 0.9}}>Up-trend</div>
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
			{/* Header */}
			<div style={{opacity: titleOpacity, marginTop: '20px', marginBottom: '30px'}}>
				<h1 style={{fontSize: '3.5rem', marginBottom: '10px', fontWeight: 800}}>📊 ETF PERFORMANCE</h1>
				<div style={{fontSize: '1.8rem', opacity: 0.8}}>Major Index Trackers</div>
			</div>

			{/* ETF Grid */}
			<div style={{
				opacity: etfOpacity,
				display: 'flex',
				flexDirection: 'column',
				gap: '20px',
				width: '100%',
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				{/* Top Row */}
				<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
					<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '2.8rem', fontWeight: 800, marginBottom: '8px'}}>SPY</div>
						<div style={{fontSize: '2.2rem', marginBottom: '8px'}}>$649.12</div>
						<div style={{fontSize: '2rem', color: '#00ff88', fontWeight: 600}}>+0.84%</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '2.8rem', fontWeight: 800, marginBottom: '8px'}}>QQQ</div>
						<div style={{fontSize: '2.2rem', marginBottom: '8px'}}>$575.23</div>
						<div style={{fontSize: '2rem', color: '#00ff88', fontWeight: 600}}>+0.91%</div>
					</div>
				</div>

				{/* Second Row */}
				<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
					<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '2.8rem', fontWeight: 800, marginBottom: '8px'}}>IWM</div>
						<div style={{fontSize: '2.2rem', marginBottom: '8px'}}>$236.59</div>
						<div style={{fontSize: '2rem', color: '#00ff88', fontWeight: 600}}>+1.25%</div>
						<div style={{fontSize: '1.8rem', opacity: 0.8, marginTop: '5px'}}>Small Caps Lead</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '2.8rem', fontWeight: 800, marginBottom: '8px'}}>DIA</div>
						<div style={{fontSize: '2.2rem', marginBottom: '8px'}}>$457.05</div>
						<div style={{fontSize: '2rem', color: '#00ff88', fontWeight: 600}}>+0.84%</div>
					</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.15)', padding: '20px', borderRadius: '20px', backdropFilter: 'blur(10px)'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 600, marginBottom: '8px'}}>💡 Key Insight</div>
					<div style={{fontSize: '2.2rem', opacity: 0.9}}>Small caps (IWM) outperforming indicates strong risk appetite</div>
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
			{/* Header */}
			<div style={{opacity: titleOpacity, marginTop: '20px', marginBottom: '30px'}}>
				<h1 style={{fontSize: '3.5rem', marginBottom: '10px', fontWeight: 800}}>🔥 VOLUME SURGE</h1>
				<div style={{fontSize: '1.8rem', opacity: 0.8}}>Top Movers Today</div>
			</div>

			{/* Stocks List */}
			<div style={{
				opacity: stocksOpacity,
				display: 'flex',
				flexDirection: 'column',
				gap: '18px',
				width: '100%',
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
					<div>
						<div style={{fontSize: '2.8rem', fontWeight: 800}}>AEO</div>
						<div style={{fontSize: '2rem', opacity: 0.8}}>105.2M vol</div>
					</div>
					<div style={{textAlign: 'right'}}>
						<div style={{fontSize: '2.4rem', marginBottom: '5px'}}>$18.79</div>
						<div style={{fontSize: '2.2rem', color: '#00ff88', fontWeight: 700}}>+37.93%</div>
					</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
					<div>
						<div style={{fontSize: '2.8rem', fontWeight: 800}}>NEGG</div>
						<div style={{fontSize: '2rem', opacity: 0.8}}>4.5M vol</div>
					</div>
					<div style={{textAlign: 'right'}}>
						<div style={{fontSize: '2.4rem', marginBottom: '5px'}}>$40.25</div>
						<div style={{fontSize: '2.2rem', color: '#00ff88', fontWeight: 700}}>+29.93%</div>
					</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
					<div>
						<div style={{fontSize: '2.8rem', fontWeight: 800}}>CIEN</div>
						<div style={{fontSize: '2rem', opacity: 0.8}}>11.3M vol</div>
					</div>
					<div style={{textAlign: 'right'}}>
						<div style={{fontSize: '2.4rem', marginBottom: '5px'}}>$116.92</div>
						<div style={{fontSize: '2.2rem', color: '#00ff88', fontWeight: 700}}>+23.29%</div>
					</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.15)', padding: '20px', borderRadius: '20px', backdropFilter: 'blur(10px)'}}>
					<div style={{fontSize: '2.4rem', fontWeight: 600, opacity: 0.9}}>Average: +6.3% with 2.4x relative volume</div>
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
			background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
			...slideStyle
		}}>
			{/* Header */}
			<div style={{opacity: titleOpacity, marginTop: '20px', marginBottom: '30px'}}>
				<h1 style={{fontSize: '3.5rem', marginBottom: '10px', fontWeight: 800}}>🏢 SECTOR ROTATION</h1>
				<div style={{fontSize: '1.8rem', opacity: 0.8}}>All Sectors Positive</div>
			</div>

			{/* Sectors List */}
			<div style={{
				opacity: sectorsOpacity,
				display: 'flex',
				flexDirection: 'column',
				gap: '16px',
				width: '100%',
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				<div style={{background: 'rgba(255,255,255,0.25)', padding: '22px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 600}}>Consumer Cyclical</div>
					<div style={{fontSize: '2.4rem', color: '#00ff88', fontWeight: 700}}>+1.82%</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.25)', padding: '22px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 600}}>Industrials</div>
					<div style={{fontSize: '2.4rem', color: '#00ff88', fontWeight: 700}}>+1.18%</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.25)', padding: '22px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 600}}>Financial</div>
					<div style={{fontSize: '2.4rem', color: '#00ff88', fontWeight: 700}}>+1.03%</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.25)', padding: '22px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 600}}>Communication</div>
					<div style={{fontSize: '2.4rem', color: '#00ff88', fontWeight: 700}}>+0.96%</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.25)', padding: '22px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 600}}>Technology</div>
					<div style={{fontSize: '2.4rem', color: '#00ff88', fontWeight: 700}}>+0.63%</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.15)', padding: '18px', borderRadius: '18px', backdropFilter: 'blur(10px)'}}>
					<div style={{fontSize: '2.4rem', fontWeight: 600, opacity: 0.9}}>💪 Broad strength across all sectors</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 5: After-Hours Earnings Winners
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
			background: 'linear-gradient(135deg, #ff6b6b 0%, #ffa500 100%)',
			...slideStyle
		}}>
			{/* Header */}
			<div style={{opacity: titleOpacity, marginTop: '20px', marginBottom: '30px'}}>
				<h1 style={{fontSize: '3.2rem', marginBottom: '10px', fontWeight: 800}}>⏰ AFTER-HOURS</h1>
				<div style={{fontSize: '1.8rem', opacity: 0.8}}>Earnings Winners</div>
			</div>

			{/* Earnings Winners */}
			<div style={{
				opacity: earningsOpacity,
				display: 'flex',
				flexDirection: 'column',
				gap: '16px',
				width: '100%',
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
					<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px'}}>
						<div style={{fontSize: '2.8rem', fontWeight: 800}}>BRZE</div>
						<div style={{fontSize: '2.4rem', color: '#00ff88', fontWeight: 700}}>+15.40%</div>
					</div>
					<div style={{fontSize: '2rem', opacity: 0.8}}>EPS Beat: +52.51% | Revenue Beat: +2.17%</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
					<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px'}}>
						<div style={{fontSize: '2.8rem', fontWeight: 800}}>GWRE</div>
						<div style={{fontSize: '2.4rem', color: '#00ff88', fontWeight: 700}}>+14.56%</div>
					</div>
					<div style={{fontSize: '2rem', opacity: 0.8}}>EPS Beat: +90.35% | Revenue Beat: +2.51%</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.25)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
					<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px'}}>
						<div style={{fontSize: '2.8rem', fontWeight: 800}}>IOT</div>
						<div style={{fontSize: '2.4rem', color: '#00ff88', fontWeight: 700}}>+8.73%</div>
					</div>
					<div style={{fontSize: '2rem', opacity: 0.8}}>EPS Beat: +89.98% | Revenue Beat: +4.40%</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.15)', padding: '18px', borderRadius: '18px', backdropFilter: 'blur(10px)'}}>
					<div style={{fontSize: '2.4rem', fontWeight: 600, opacity: 0.9}}>🎯 Tech sector dominating earnings</div>
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

	const footerOpacity = interpolate(frame, [60, 90], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
			...slideStyle
		}}>
			{/* Header */}
			<div style={{opacity: titleOpacity, marginTop: '20px', marginBottom: '30px'}}>
				<h1 style={{fontSize: '3.5rem', marginBottom: '10px', fontWeight: 800}}>🔍 KEY TAKEAWAYS</h1>
				<div style={{fontSize: '1.8rem', opacity: 0.8}}>September 4, 2025</div>
			</div>

			{/* Key Points */}
			<div style={{
				opacity: takeawaysOpacity,
				display: 'flex',
				flexDirection: 'column',
				gap: '20px',
				width: '100%',
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '2.4rem', fontWeight: 600, marginBottom: '8px'}}>💪 Broad Market Strength</div>
					<div style={{fontSize: '2rem', opacity: 0.8}}>All major sectors positive, small caps outperforming</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.2)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '2.4rem', fontWeight: 600, marginBottom: '8px'}}>🔥 Volume Activity</div>
					<div style={{fontSize: '2rem', opacity: 0.8}}>81 volume-surge stocks, avg +6.3% gains</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.2)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '2.4rem', fontWeight: 600, marginBottom: '8px'}}>🎯 Earnings Excellence</div>
					<div style={{fontSize: '2rem', opacity: 0.8}}>Strong tech earnings beats driving AH momentum</div>
				</div>

				<div style={{background: 'rgba(255,255,255,0.2)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '2.4rem', fontWeight: 600, marginBottom: '8px'}}>📈 Risk-On Environment</div>
					<div style={{fontSize: '2rem', opacity: 0.8}}>Consumer cyclical leading, bonds up, gold down</div>
				</div>
			</div>

			{/* Footer */}
			<div style={{opacity: footerOpacity, textAlign: 'center', marginBottom: '20px'}}>
				<div style={{fontSize: '2rem', fontWeight: 600, marginBottom: '8px'}}>Follow for daily market updates</div>
				<div style={{fontSize: '1.8rem', opacity: 0.7}}>Data: Finviz.com, Alpaca Markets</div>
			</div>
		</AbsoluteFill>
	);
};

// Main component with sequences
export const AfterMarketSlides: React.FC = () => {
	const {fps} = useVideoConfig();
	
	const slideDuration = fps * 4; // 4 seconds per slide
	
	return (
		<>
			<Sequence name="Title Slide" from={0} durationInFrames={slideDuration}>
				<Slide1 />
			</Sequence>
			
			<Sequence name="ETF Performance" from={slideDuration} durationInFrames={slideDuration}>
				<Slide2 />
			</Sequence>
			
			<Sequence name="Volume Surge" from={slideDuration * 2} durationInFrames={slideDuration}>
				<Slide3 />
			</Sequence>
			
			<Sequence name="Sector Performance" from={slideDuration * 3} durationInFrames={slideDuration}>
				<Slide4 />
			</Sequence>
			
			<Sequence name="After Hours Earnings" from={slideDuration * 4} durationInFrames={slideDuration}>
				<Slide5 />
			</Sequence>
			
			<Sequence name="Key Takeaways" from={slideDuration * 5} durationInFrames={slideDuration}>
				<Slide6 />
			</Sequence>
		</>
	);
};