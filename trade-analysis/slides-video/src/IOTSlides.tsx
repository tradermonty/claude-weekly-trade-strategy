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

const Slide1: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const metricsOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const logoOpacity = interpolate(frame, [60, 90], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
			...slideStyle
		}}>
			{/* Header Section */}
			<div style={{opacity: titleOpacity, textAlign: 'center', marginTop: '20px'}}>
				<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '15px'}}>NYSE: IOT</div>
				<h1 style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>SAMSARA</h1>
				<h2 style={{fontSize: '3rem', fontWeight: 800, marginBottom: '20px', lineHeight: 1.1}}>Q2 2026</h2>
				<div style={{fontSize: '2rem', fontWeight: 300, opacity: 0.9, marginBottom: '25px'}}>Connected Operations Leader</div>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600}}>
					September 4, 2025
				</div>
			</div>
			
			{/* Metrics Section */}
			<div style={{
				opacity: metricsOpacity, 
				display: 'flex',
				flexDirection: 'column',
				gap: '25px', 
				width: '100%', 
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '4rem', marginBottom: '15px', fontWeight: 800}}>
						$391.5M <span style={{background: '#00b894', padding: '10px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600, marginLeft: '20px'}}>BEAT</span>
					</div>
					<div style={{fontSize: '2rem', opacity: 0.9, marginBottom: '10px'}}>Revenue (+30% YoY)</div>
					<div style={{fontSize: '2rem', opacity: 0.7}}>Strong Enterprise Growth</div>
				</div>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '4rem', marginBottom: '15px', fontWeight: 800}}>
						$1.64B <span style={{background: '#00b894', padding: '10px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600, marginLeft: '20px'}}>ARR</span>
					</div>
					<div style={{fontSize: '2rem', opacity: 0.9, marginBottom: '10px'}}>Annual Recurring Revenue</div>
					<div style={{fontSize: '2rem', opacity: 0.7}}>+30% YoY Growth</div>
				</div>
				<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800}}>15%</div>
						<div style={{fontSize: '2rem', opacity: 0.9}}>Operating</div>
						<div style={{fontSize: '1.7rem', opacity: 0.7}}>Margin</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800}}>2,771</div>
						<div style={{fontSize: '2rem', opacity: 0.9}}>Enterprise</div>
						<div style={{fontSize: '1.7rem', opacity: 0.7}}>Customers</div>
					</div>
				</div>
			</div>
			
			{/* Footer Section */}
			<div style={{opacity: logoOpacity, textAlign: 'center', marginBottom: '10px'}}>
				<div style={{fontSize: '2.2rem', fontWeight: 600, marginBottom: '10px'}}>Current Price: $35.84</div>
				<div style={{fontSize: '2rem', opacity: 0.8}}>Market Cap: $20.4B</div>
				<div style={{fontSize: '1.8rem', opacity: 0.6, marginTop: '12px'}}>IoT Operations Platform</div>
			</div>
		</AbsoluteFill>
	);
};

const Slide2: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const metricsOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const highlightsOpacity = interpolate(frame, [60, 90], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const bottomOpacity = interpolate(frame, [90, 120], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #74b9ff 0%, #0984e3 100%)',
			...slideStyle
		}}>
			{/* Header */}
			<div style={{opacity: titleOpacity}}>
				<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '15px'}}>CONNECTED OPERATIONS</div>
				<h1 style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>IoT PLATFORM</h1>
				<h2 style={{fontSize: '2.2rem', fontWeight: 300, opacity: 0.9}}>Exceptional Growth & Margins</h2>
			</div>
			
			{/* Key Metrics */}
			<div style={{
				opacity: metricsOpacity, 
				display: 'flex',
				flexDirection: 'column',
				gap: '25px', 
				width: '100%', 
				maxWidth: '900px'
			}}>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '35px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, color: '#fdcb6e'}}>+900bps</div>
					<div style={{fontSize: '2.2rem', opacity: 0.9, marginBottom: '8px'}}>Operating Margin Expansion</div>
					<div style={{fontSize: '1.8rem', fontWeight: 600, color: '#00b894'}}>From 6% to 15% YoY</div>
				</div>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '35px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, color: '#fdcb6e'}}>$44.2M</div>
					<div style={{fontSize: '2.2rem', opacity: 0.9, marginBottom: '8px'}}>Adjusted Free Cash Flow</div>
					<div style={{fontSize: '1.8rem', fontWeight: 600, opacity: 0.8}}>+238% YoY Growth</div>
				</div>
			</div>

			{/* Key Highlights */}
			<div style={{opacity: highlightsOpacity, fontSize: '2rem', lineHeight: '1.8', width: '100%', maxWidth: '900px', textAlign: 'left'}}>
				<div style={{marginBottom: '20px', display: 'flex', alignItems: 'flex-start'}}>
					<span style={{color: '#fdcb6e', fontSize: '2.2rem', marginRight: '15px', marginTop: '2px'}}>★</span>
					<span>651 new enterprise customers ($100K+ ARR) added</span>
				</div>
				<div style={{marginBottom: '20px', display: 'flex', alignItems: 'flex-start'}}>
					<span style={{color: '#fdcb6e', fontSize: '2.2rem', marginRight: '15px', marginTop: '2px'}}>★</span>
					<span>Million-dollar customers: 20%+ of total ARR</span>
				</div>
				<div style={{marginBottom: '20px', display: 'flex', alignItems: 'flex-start'}}>
					<span style={{color: '#fdcb6e', fontSize: '2.2rem', marginRight: '15px', marginTop: '2px'}}>★</span>
					<span>AI-powered operational insights driving growth</span>
				</div>
				<div style={{marginBottom: '20px', display: 'flex', alignItems: 'flex-start'}}>
					<span style={{color: '#fdcb6e', fontSize: '2.2rem', marginRight: '15px', marginTop: '2px'}}>★</span>
					<span>Strong retention and expansion metrics</span>
				</div>
			</div>
			
			{/* Bottom Message */}
			<div style={{opacity: bottomOpacity, textAlign: 'center'}}>
				<div style={{fontSize: '2rem', fontWeight: 700, marginBottom: '10px'}}>Market Leadership</div>
				<div style={{fontSize: '2rem', opacity: 0.9}}>in Industrial IoT</div>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '2rem', marginTop: '18px', display: 'inline-block'}}>
					Connected Operations Cloud
				</div>
			</div>
		</AbsoluteFill>
	);
};

const Slide3: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const guidanceOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const targetsOpacity = interpolate(frame, [60, 90], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #00cec9 0%, #55a3ff 100%)',
			...slideStyle
		}}>
			{/* Header */}
			<div style={{opacity: titleOpacity}}>
				<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '15px'}}>FORWARD OUTLOOK</div>
				<h1 style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>GROWTH RUNWAY</h1>
				<h2 style={{fontSize: '2.2rem', fontWeight: 300, opacity: 0.9}}>Raised Guidance & Strong Pipeline</h2>
			</div>
			
			{/* Guidance Metrics */}
			<div style={{
				opacity: guidanceOpacity, 
				display: 'flex', 
				flexDirection: 'column',
				gap: '20px', 
				width: '100%', 
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)', textAlign: 'center'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800, color: '#fdcb6e'}}>~$420M</div>
						<div style={{fontSize: '2rem', opacity: 0.9, lineHeight: '1.3', marginBottom: '8px'}}>Q3 Revenue</div>
						<div style={{fontSize: '1.8rem', opacity: 0.7}}>Target</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)', textAlign: 'center'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800, color: '#00b894'}}>25%+</div>
						<div style={{fontSize: '2rem', opacity: 0.9, lineHeight: '1.3', marginBottom: '8px'}}>ARR Growth</div>
						<div style={{fontSize: '1.8rem', opacity: 0.7}}>Continued</div>
					</div>
				</div>
				<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)', textAlign: 'center'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800, color: '#fdcb6e'}}>78%</div>
						<div style={{fontSize: '2rem', opacity: 0.9, lineHeight: '1.3', marginBottom: '8px'}}>Gross Margin</div>
						<div style={{fontSize: '1.8rem', opacity: 0.7}}>Stable</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)', textAlign: 'center'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800, color: '#e74c3c'}}>$1.8B+</div>
						<div style={{fontSize: '2rem', opacity: 0.9, lineHeight: '1.3', marginBottom: '8px'}}>FY ARR</div>
						<div style={{fontSize: '1.8rem', opacity: 0.7}}>Target</div>
					</div>
				</div>
				<div style={{background: 'rgba(255,255,255,0.15)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', textAlign: 'center'}}>
					<div style={{fontSize: '1.8rem', fontWeight: 600, marginBottom: '12px'}}>Revenue Progression</div>
					<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '2rem'}}>
						<span>Q2: $391.5M</span>
						<span style={{fontSize: '2rem'}}>→</span>
						<span style={{fontWeight: 800}}>Q3: ~$420M</span>
					</div>
				</div>
			</div>

			{/* Analyst Targets */}
			<div style={{opacity: targetsOpacity, textAlign: 'center'}}>
				<div style={{fontSize: '2rem', fontWeight: 600, marginBottom: '18px'}}>Investment Outlook</div>
				<div style={{fontSize: '3.8rem', fontWeight: 800, color: '#fdcb6e', marginBottom: '12px'}}>$45-55</div>
				<div style={{fontSize: '2rem', opacity: 0.9, marginBottom: '18px'}}>Fair Value Range</div>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '15px 25px', borderRadius: '30px', fontSize: '2rem', fontWeight: 600, display: 'inline-block'}}>
					Strong Fundamentals
				</div>
			</div>
		</AbsoluteFill>
	);
};

const Slide4: React.FC = () => {
	const frame = useCurrentFrame();
	
	const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
		extrapolateRight: 'clamp',
	});
	
	const analysisOpacity = interpolate(frame, [30, 60], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const bottomOpacity = interpolate(frame, [60, 90], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #ff7675 0%, #fd79a8 100%)',
			...slideStyle
		}}>
			{/* Header */}
			<div style={{opacity: titleOpacity}}>
				<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '15px'}}>INVESTMENT ANALYSIS</div>
				<h1 style={{fontSize: '4rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>HOLD/WATCH</h1>
				<h1 style={{fontSize: '4rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>RATING</h1>
				<h2 style={{fontSize: '2.2rem', fontWeight: 300, opacity: 0.9}}>Risk vs Opportunity</h2>
			</div>
			
			{/* Analysis Content */}
			<div style={{
				opacity: analysisOpacity, 
				display: 'flex', 
				flexDirection: 'column',
				gap: '25px', 
				width: '100%', 
				maxWidth: '900px',
				flex: 1,
				justifyContent: 'center'
			}}>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '35px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 700, marginBottom: '25px', textAlign: 'center'}}>🐂 BULL CASE</div>
					<div style={{fontSize: '2rem', lineHeight: '1.8', textAlign: 'left'}}>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>Market leadership in industrial IoT</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>900bps margin expansion capability</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>Strong enterprise customer stickiness</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>AI-powered differentiation</span>
						</div>
						<div style={{display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>Large addressable market opportunity</span>
						</div>
					</div>
				</div>
				
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '35px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 700, marginBottom: '25px', textAlign: 'center'}}>🐻 BEAR CASE</div>
					<div style={{fontSize: '2rem', lineHeight: '1.8', textAlign: 'left'}}>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>High valuation (15.3x P/S) risk</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Competitive threats from tech giants</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Economic sensitivity of B2B spending</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Growth rate sustainability concerns</span>
						</div>
						<div style={{display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Execution risk at higher scale</span>
						</div>
					</div>
				</div>
			</div>
			
			{/* Bottom Summary */}
			<div style={{opacity: bottomOpacity, textAlign: 'center'}}>
				<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '12px'}}>Investment Summary</div>
				<div style={{fontSize: '2rem', opacity: 0.9, marginBottom: '15px'}}>Strong business, premium valuation</div>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 22px', borderRadius: '25px', fontSize: '1.8rem', display: 'inline-block'}}>
					Target Entry: $32-34 Range
				</div>
			</div>
		</AbsoluteFill>
	);
};

export const IOTSlides: React.FC = () => {
	return (
		<>
			<Sequence from={0} durationInFrames={180}>
				<Slide1 />
			</Sequence>
			<Sequence from={180} durationInFrames={180}>
				<Slide2 />
			</Sequence>
			<Sequence from={360} durationInFrames={180}>
				<Slide3 />
			</Sequence>
			<Sequence from={540} durationInFrames={180}>
				<Slide4 />
			</Sequence>
		</>
	);
};