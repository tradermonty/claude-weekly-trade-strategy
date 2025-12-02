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
				<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '15px'}}>NASDAQ: AVGO</div>
				<h1 style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>BROADCOM</h1>
				<h2 style={{fontSize: '3rem', fontWeight: 800, marginBottom: '20px', lineHeight: 1.1}}>Q3 2025</h2>
				<div style={{fontSize: '2rem', fontWeight: 300, opacity: 0.9, marginBottom: '25px'}}>Strong AI-Driven Quarter</div>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600}}>
					September 5, 2025
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
						$15.96B <span style={{background: '#00b894', padding: '10px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600, marginLeft: '20px'}}>BEAT</span>
					</div>
					<div style={{fontSize: '2rem', opacity: 0.9, marginBottom: '10px'}}>Revenue (+22% YoY)</div>
					<div style={{fontSize: '2rem', opacity: 0.7}}>vs $15.83B consensus</div>
				</div>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '4rem', marginBottom: '15px', fontWeight: 800}}>
						$1.69 <span style={{background: '#00b894', padding: '10px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600, marginLeft: '20px'}}>BEAT</span>
					</div>
					<div style={{fontSize: '2rem', opacity: 0.9, marginBottom: '10px'}}>Adjusted EPS (+132% YoY)</div>
					<div style={{fontSize: '2rem', opacity: 0.7}}>vs $1.65 consensus</div>
				</div>
				<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800}}>+4.5%</div>
						<div style={{fontSize: '2rem', opacity: 0.9}}>After Hours</div>
						<div style={{fontSize: '1.7rem', opacity: 0.7}}>Move</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800}}>$7.0B</div>
						<div style={{fontSize: '2rem', opacity: 0.9}}>Free Cash</div>
						<div style={{fontSize: '1.7rem', opacity: 0.7}}>Flow</div>
					</div>
				</div>
			</div>
			
			{/* Footer Section */}
			<div style={{opacity: logoOpacity, textAlign: 'center', marginBottom: '10px'}}>
				<div style={{fontSize: '2.2rem', fontWeight: 600, marginBottom: '10px'}}>Current Price: $320.15</div>
				<div style={{fontSize: '2rem', opacity: 0.8}}>Market Cap: $1.44T</div>
				<div style={{fontSize: '1.8rem', opacity: 0.6, marginTop: '12px'}}>52-Week Performance: +88%</div>
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
				<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '15px'}}>ARTIFICIAL INTELLIGENCE</div>
				<h1 style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>AI MOMENTUM</h1>
				<h2 style={{fontSize: '2.2rem', fontWeight: 300, opacity: 0.9}}>Leading the AI Revolution</h2>
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
					<div style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, color: '#fdcb6e'}}>$5.2B</div>
					<div style={{fontSize: '2.2rem', opacity: 0.9, marginBottom: '8px'}}>AI Revenue</div>
					<div style={{fontSize: '1.8rem', fontWeight: 600, color: '#00b894'}}>+63% YoY Growth</div>
				</div>
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '35px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, color: '#fdcb6e'}}>$10B</div>
					<div style={{fontSize: '2.2rem', opacity: 0.9, marginBottom: '8px'}}>New Customer Orders</div>
					<div style={{fontSize: '1.8rem', fontWeight: 600, opacity: 0.8}}>Custom AI Chips</div>
				</div>
			</div>

			{/* Key Highlights */}
			<div style={{opacity: highlightsOpacity, fontSize: '2rem', lineHeight: '1.8', width: '100%', maxWidth: '900px', textAlign: 'left'}}>
				<div style={{marginBottom: '20px', display: 'flex', alignItems: 'flex-start'}}>
					<span style={{color: '#fdcb6e', fontSize: '2.2rem', marginRight: '15px', marginTop: '2px'}}>★</span>
					<span>AI semiconductor revenue jumped 63% to $5.2 billion</span>
				</div>
				<div style={{marginBottom: '20px', display: 'flex', alignItems: 'flex-start'}}>
					<span style={{color: '#fdcb6e', fontSize: '2.2rem', marginRight: '15px', marginTop: '2px'}}>★</span>
					<span>Secured $10B in orders from new AI customer</span>
				</div>
				<div style={{marginBottom: '20px', display: 'flex', alignItems: 'flex-start'}}>
					<span style={{color: '#fdcb6e', fontSize: '2.2rem', marginRight: '15px', marginTop: '2px'}}>★</span>
					<span>Q4 AI revenue guidance: $6.2B (accelerating growth)</span>
				</div>
				<div style={{marginBottom: '20px', display: 'flex', alignItems: 'flex-start'}}>
					<span style={{color: '#fdcb6e', fontSize: '2.2rem', marginRight: '15px', marginTop: '2px'}}>★</span>
					<span>Dominant position in hyperscaler custom AI chips</span>
				</div>
			</div>
			
			{/* Bottom Message */}
			<div style={{opacity: bottomOpacity, textAlign: 'center'}}>
				<div style={{fontSize: '2rem', fontWeight: 700, marginBottom: '10px'}}>Go-to AI Supplier</div>
				<div style={{fontSize: '2rem', opacity: 0.9}}>for Custom Solutions</div>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '2rem', marginTop: '18px', display: 'inline-block'}}>
					Market Leader in AI Chips
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
				<div style={{fontSize: '2rem', opacity: 0.8, marginBottom: '15px'}}>FISCAL YEAR 2025</div>
				<h1 style={{fontSize: '4.5rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>Q4 GUIDANCE</h1>
				<h2 style={{fontSize: '2.2rem', fontWeight: 300, opacity: 0.9}}>Beating Street Expectations</h2>
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
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800, color: '#fdcb6e'}}>$17.4B</div>
						<div style={{fontSize: '2rem', opacity: 0.9, lineHeight: '1.3', marginBottom: '8px'}}>Q4 Revenue</div>
						<div style={{fontSize: '1.8rem', opacity: 0.7}}>(vs $17.02B consensus)</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)', textAlign: 'center'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800, color: '#00b894'}}>+24%</div>
						<div style={{fontSize: '2rem', opacity: 0.9, lineHeight: '1.3', marginBottom: '8px'}}>Revenue Growth</div>
						<div style={{fontSize: '1.8rem', opacity: 0.7}}>Year-over-Year</div>
					</div>
				</div>
				<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)', textAlign: 'center'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800, color: '#fdcb6e'}}>67%</div>
						<div style={{fontSize: '2rem', opacity: 0.9, lineHeight: '1.3', marginBottom: '8px'}}>EBITDA Margin</div>
						<div style={{fontSize: '1.8rem', opacity: 0.7}}>Adjusted</div>
					</div>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)', textAlign: 'center'}}>
						<div style={{fontSize: '3.2rem', marginBottom: '12px', fontWeight: 800, color: '#e74c3c'}}>$6.2B</div>
						<div style={{fontSize: '2rem', opacity: 0.9, lineHeight: '1.3', marginBottom: '8px'}}>AI Revenue</div>
						<div style={{fontSize: '1.8rem', opacity: 0.7}}>Q4 Target</div>
					</div>
				</div>
				<div style={{background: 'rgba(255,255,255,0.15)', padding: '30px', borderRadius: '20px', backdropFilter: 'blur(10px)', textAlign: 'center'}}>
					<div style={{fontSize: '1.8rem', fontWeight: 600, marginBottom: '12px'}}>Revenue Progression</div>
					<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '2rem'}}>
						<span>Q3: $15.96B</span>
						<span style={{fontSize: '2rem'}}>→</span>
						<span style={{fontWeight: 800}}>Q4: $17.4B</span>
					</div>
				</div>
			</div>

			{/* Analyst Targets */}
			<div style={{opacity: targetsOpacity, textAlign: 'center'}}>
				<div style={{fontSize: '2rem', fontWeight: 600, marginBottom: '18px'}}>Analyst Price Targets</div>
				<div style={{fontSize: '3.8rem', fontWeight: 800, color: '#fdcb6e', marginBottom: '12px'}}>$325 - $400</div>
				<div style={{fontSize: '2rem', opacity: 0.9, marginBottom: '18px'}}>Average upside: +12%</div>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '15px 25px', borderRadius: '30px', fontSize: '2rem', fontWeight: 600, display: 'inline-block'}}>
					Strong Forward Momentum
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
				<h1 style={{fontSize: '4rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>INVESTMENT</h1>
				<h1 style={{fontSize: '4rem', marginBottom: '15px', fontWeight: 800, lineHeight: 1.1}}>THESIS</h1>
				<h2 style={{fontSize: '2.2rem', fontWeight: 300, opacity: 0.9}}>Bull vs Bear Case</h2>
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
							<span>AI market leader with 63% growth</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>$10B new customer expansion</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>67% EBITDA margins & pricing power</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>$7B+ quarterly free cash flow</span>
						</div>
						<div style={{display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#27ae60', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↗</span>
							<span>VMware synergies delivering results</span>
						</div>
					</div>
				</div>
				
				<div style={{background: 'rgba(255,255,255,0.2)', padding: '35px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.3)'}}>
					<div style={{fontSize: '2.2rem', fontWeight: 700, marginBottom: '25px', textAlign: 'center'}}>🐻 BEAR CASE</div>
					<div style={{fontSize: '2rem', lineHeight: '1.8', textAlign: 'left'}}>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Forward P/E of 37x premium valuation</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Customer concentration risk</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Cyclical semiconductor exposure</span>
						</div>
						<div style={{marginBottom: '15px', display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Increasing AI chip competition</span>
						</div>
						<div style={{display: 'flex', alignItems: 'center'}}>
							<span style={{color: '#e74c3c', marginRight: '12px', fontSize: '1.6rem', fontWeight: 'bold'}}>↘</span>
							<span>Macro sensitivity concerns</span>
						</div>
					</div>
				</div>
			</div>
			
			{/* Bottom Summary */}
			<div style={{opacity: bottomOpacity, textAlign: 'center'}}>
				<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '12px'}}>Investment Summary</div>
				<div style={{fontSize: '2rem', opacity: 0.9, marginBottom: '15px'}}>Strong fundamentals vs valuation concerns</div>
				<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 22px', borderRadius: '25px', fontSize: '1.8rem', display: 'inline-block'}}>
					Generated: September 5, 2025
				</div>
			</div>
		</AbsoluteFill>
	);
};

export const AVGOSlides: React.FC = () => {
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