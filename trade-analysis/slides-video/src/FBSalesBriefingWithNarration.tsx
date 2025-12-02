import React from 'react';
import {
	AbsoluteFill,
	interpolate,
	useCurrentFrame,
	useVideoConfig,
	Sequence,
	spring,
	Audio,
	staticFile,
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

// Slide 1: Title Slide (12s)
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

	const subtitleOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const executiveOpacity = interpolate(frame, [80, 120], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #5a8fd8 0%, #6da3e5 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '30px', width: '100%'}}>
				{/* Header Section */}
				<div style={{transform: `scale(${titleScale})`, textAlign: 'center'}}>
					<div style={{fontSize: '2.2rem', opacity: 0.8, marginBottom: '10px'}}>📊 Food & Beverage</div>
					<h1 style={{fontSize: '3.8rem', marginBottom: '15px', fontWeight: 900, lineHeight: 1.1, textShadow: '2px 2px 4px rgba(0,0,0,0.3)'}}>SALES BRIEFING</h1>
				</div>

				<div style={{opacity: subtitleOpacity, textAlign: 'center'}}>
					<h2 style={{fontSize: '2.6rem', fontWeight: 700, marginBottom: '20px', lineHeight: 1.1}}>April–August 2025</h2>
					<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600}}>
						Results & Forward Actions
					</div>
				</div>

				{/* Executive Level */}
				<div style={{
					opacity: executiveOpacity,
					width: '100%',
					maxWidth: '650px'
				}}>
					<div style={{background: 'rgba(255,255,255,0.2)', padding: '25px', borderRadius: '20px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.3)'}}>
						<div style={{fontSize: '2.2rem', marginBottom: '8px', fontWeight: 700, color: '#ffffff'}}>
							For Executive Leadership
						</div>
						<div style={{fontSize: '1.6rem', opacity: 0.9}}>Strategic Analysis & Action Items</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Copy all slide components from the original FBSalesBriefing.tsx

// Slide 2: Why This Matters (17s)
const Slide2: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const pointsOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #8e9efc 0%, #9f7fc4 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>🎯 WHY THIS MATTERS</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>Summer Performance Overview</div>
				</div>

				{/* Key Points */}
				<div style={{
					opacity: pointsOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '20px',
					width: '100%',
					maxWidth: '800px'
				}}>
					<div style={{background: 'rgba(76,175,80,0.3)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '3px solid #4CAF50'}}>
						<div style={{fontSize: '2.2rem', fontWeight: 800, marginBottom: '8px', color: '#4CAF50'}}>STRONG GROWTH</div>
						<div style={{fontSize: '1.8rem', marginBottom: '5px'}}>+3.5% Revenue Growth</div>
						<div style={{fontSize: '1.8rem'}}>+4.8% Unit Growth vs April</div>
					</div>

					<div style={{background: 'rgba(255,193,7,0.25)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid #FFC107'}}>
						<div style={{fontSize: '2rem', fontWeight: 700, marginBottom: '8px', color: '#FFC107'}}>⚠️ HIDDEN CONCERNS</div>
						<div style={{fontSize: '1.6rem', marginBottom: '5px'}}>Appetizer & ICEE weakness</div>
						<div style={{fontSize: '1.6rem'}}>Requires immediate attention</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.2)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', textAlign: 'center'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700}}>🍂 Critical timing for fall promotions</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 3: Financial Performance (15s)
const Slide3: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const dataOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const insightOpacity = interpolate(frame, [120, 160], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
			...slideStyle,
			color: '#2c3e50'
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>💰 FINANCIAL PERFORMANCE</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>April → August 2025</div>
				</div>

				{/* Financial Data */}
				<div style={{
					opacity: dataOpacity,
					display: 'grid',
					gridTemplateColumns: '1fr 1fr',
					gap: '15px',
					width: '100%',
					maxWidth: '750px'
				}}>
					<div style={{
						background: 'rgba(255,255,255,0.25)',
						padding: '20px',
						borderRadius: '18px',
						backdropFilter: 'blur(10px)',
						border: '2px solid rgba(255,255,255,0.4)'
					}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px'}}>April Revenue</div>
						<div style={{fontSize: '2.6rem', fontWeight: 900, color: '#4CAF50'}}>$2.196M</div>
					</div>
					<div style={{
						background: 'rgba(255,255,255,0.25)',
						padding: '20px',
						borderRadius: '18px',
						backdropFilter: 'blur(10px)',
						border: '2px solid rgba(255,255,255,0.4)'
					}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px'}}>August Revenue</div>
						<div style={{fontSize: '2.6rem', fontWeight: 900, color: '#4CAF50'}}>$2.272M</div>
					</div>
				</div>

				{/* Key Highlights */}
				<div style={{
					opacity: insightOpacity,
					width: '100%',
					maxWidth: '750px'
				}}>
					<div style={{
						background: 'rgba(255,255,255,0.2)',
						padding: '25px',
						borderRadius: '20px',
						backdropFilter: 'blur(10px)',
						border: '2px solid rgba(255,255,255,0.3)'
					}}>
						<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '15px', color: '#4CAF50'}}>
							✅ MOMENTUM REGAINED
						</div>
						<div style={{fontSize: '1.8rem', marginBottom: '8px'}}>Recovered after May dip</div>
						<div style={{fontSize: '1.6rem', opacity: 0.9}}>Unit softness in August: 443.1K vs 448.6K (July)</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 4: Category Performance (22s)
const Slide4: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const topPerformersOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const concernsOpacity = interpolate(frame, [120, 160], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #f7c6fa 0%, #faa0ad 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '2.8rem', marginBottom: '8px', fontWeight: 900}}>📊 CATEGORY PERFORMANCE</h1>
					<div style={{fontSize: '1.5rem', opacity: 0.8}}>Apr-Aug Growth Leaders & Concerns</div>
				</div>

				{/* Top Performers */}
				<div style={{
					opacity: topPerformersOpacity,
					width: '100%',
					maxWidth: '800px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '12px', textAlign: 'center', color: '#4CAF50'}}>🚀 TOP PERFORMERS</div>
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '20px'}}>
						<div style={{
							background: 'rgba(76,175,80,0.3)',
							padding: '18px 12px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '3px solid #4CAF50'
						}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>Dessert</div>
							<div style={{fontSize: '2.2rem', color: '#4CAF50', fontWeight: 900}}>+11.6%</div>
							<div style={{fontSize: '1.3rem', opacity: 0.9}}>10.1% share</div>
						</div>
						<div style={{
							background: 'rgba(76,175,80,0.3)',
							padding: '18px 12px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '3px solid #4CAF50'
						}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>Japanese</div>
							<div style={{fontSize: '2.2rem', color: '#4CAF50', fontWeight: 900}}>+8.8%</div>
							<div style={{fontSize: '1.3rem', opacity: 0.9}}>10.5% share</div>
						</div>
						<div style={{
							background: 'rgba(76,175,80,0.3)',
							padding: '18px 12px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '3px solid #4CAF50'
						}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>ICEE</div>
							<div style={{fontSize: '2.2rem', color: '#4CAF50', fontWeight: 900}}>+9.0%</div>
							<div style={{fontSize: '1.3rem', opacity: 0.9}}>3.5% share</div>
						</div>
					</div>
				</div>

				{/* Concerns */}
				<div style={{
					opacity: concernsOpacity,
					width: '100%',
					maxWidth: '800px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '12px', textAlign: 'center', color: '#ff6b6b'}}>⚠️ CONCERNS</div>
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px'}}>
						<div style={{
							background: 'rgba(255,107,107,0.25)',
							padding: '18px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '2px solid rgba(255,107,107,0.4)'
						}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>Appetizer Softness</div>
							<div style={{fontSize: '2rem', color: '#ff6b6b', fontWeight: 800}}>-0.6%</div>
							<div style={{fontSize: '1.4rem', opacity: 0.9}}>Despite 32.6% share</div>
						</div>
						<div style={{
							background: 'rgba(76,175,80,0.25)',
							padding: '18px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '2px solid rgba(76,175,80,0.4)'
						}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>Pizza Solid</div>
							<div style={{fontSize: '2rem', color: '#4CAF50', fontWeight: 800}}>+3.5%</div>
							<div style={{fontSize: '1.4rem', opacity: 0.9}}>25.9% share</div>
						</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 5: Growth Leaders (24s)
const Slide5: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const leadersOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #85c3ff 0%, #66f6ff 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>🏆 GROWTH LEADERS</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>Double Down Opportunities</div>
				</div>

				{/* Growth Leaders */}
				<div style={{
					opacity: leadersOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '15px',
					width: '100%',
					maxWidth: '800px'
				}}>
					{[
						{name: 'ICEE Float', growth: '+56%', action: 'Expand marketing tie-ins'},
						{name: 'Chicken Sandwich Combos', growth: '+32-51%', action: 'Maintain pricing'},
						{name: 'Cheese Fries Upsize', growth: '+44-47%', action: 'Digital menu push'},
						{name: 'JP Chashu Bowl', growth: '+39%', action: 'Premium positioning'},
					].map((item, index) => (
						<div key={index} style={{
							background: 'rgba(255,255,255,0.25)',
							padding: '18px 20px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '2px solid rgba(255,255,255,0.4)',
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center'
						}}>
							<div>
								<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '5px'}}>{item.name}</div>
								<div style={{fontSize: '1.4rem', opacity: 0.9}}>{item.action}</div>
							</div>
							<div style={{fontSize: '2.4rem', color: '#4CAF50', fontWeight: 900}}>{item.growth}</div>
						</div>
					))}
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 6: Revenue Drags (18s)
const Slide6: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const dragsOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const interventionOpacity = interpolate(frame, [120, 160], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #ffa0b4 0%, #8da4f1 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>📉 REVENUE DRAGS</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>Immediate Stabilization Needed</div>
				</div>

				{/* Problem Items */}
				<div style={{
					opacity: dragsOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '15px',
					width: '100%',
					maxWidth: '800px'
				}}>
					{[
						{name: 'Classic ICEE Flavors', decline: '-22 to -37%', issue: 'Refresh flavor rotation'},
						{name: 'Wing Platter', decline: '-28%', issue: 'Assess portion value'},
						{name: 'Extra Beef Patty', decline: '-22%', issue: 'Revisit upsell scripts'},
					].map((item, index) => (
						<div key={index} style={{
							background: 'rgba(255,107,107,0.25)',
							padding: '18px 20px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '2px solid rgba(255,107,107,0.4)',
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center'
						}}>
							<div>
								<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '5px'}}>{item.name}</div>
								<div style={{fontSize: '1.4rem', opacity: 0.9}}>{item.issue}</div>
							</div>
							<div style={{fontSize: '2.2rem', color: '#ff6b6b', fontWeight: 900}}>{item.decline}</div>
						</div>
					))}
				</div>

				{/* Call to Action */}
				<div style={{
					opacity: interventionOpacity,
					background: 'rgba(255,255,255,0.2)',
					padding: '20px',
					borderRadius: '18px',
					backdropFilter: 'blur(10px)',
					border: '2px solid rgba(255,255,255,0.3)',
					width: '100%',
					maxWidth: '800px'
				}}>
					<div style={{fontSize: '2rem', fontWeight: 800, textAlign: 'center', color: '#ffeb3b'}}>
						⚡ INTERVENTION REQUIRED
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 7: Operational Issues (16s)
const Slide7: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const issuesOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const solutionOpacity = interpolate(frame, [120, 160], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #fca5c1 0%, #fff0a0 100%)',
			color: '#2c3e50',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900, color: '#c62828'}}>🚨 OPERATIONAL ISSUES</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8, color: '#2c3e50', fontWeight: 600}}>Critical System Problems</div>
				</div>

				{/* Issues */}
				<div style={{
					opacity: issuesOpacity,
					width: '100%',
					maxWidth: '800px'
				}}>
					<div style={{
						background: 'rgba(198,40,40,0.15)',
						padding: '20px',
						borderRadius: '18px',
						backdropFilter: 'blur(10px)',
						border: '3px solid #c62828',
						marginBottom: '20px'
					}}>
						<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '15px', color: '#c62828'}}>
							❌ ZERO-SALES MONTHS
						</div>
						<div style={{fontSize: '1.6rem', marginBottom: '8px', color: '#2c3e50', fontWeight: 600}}>
							• JP Japanese Combo
						</div>
						<div style={{fontSize: '1.6rem', marginBottom: '8px', color: '#2c3e50', fontWeight: 600}}>
							• Pizza LG Half Topping Extra Cheese
						</div>
						<div style={{fontSize: '1.6rem', color: '#2c3e50', fontWeight: 600}}>
							• Burger Combo
						</div>
					</div>

					<div style={{
						background: 'rgba(255,193,7,0.2)',
						padding: '18px',
						borderRadius: '15px',
						backdropFilter: 'blur(10px)',
						border: '2px solid #FFC107'
					}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px', color: '#2c3e50'}}>
							Suspected: POS/inventory issues
						</div>
					</div>
				</div>

				{/* Solution */}
				<div style={{
					opacity: solutionOpacity,
					background: 'rgba(76,175,80,0.2)',
					padding: '20px',
					borderRadius: '18px',
					backdropFilter: 'blur(10px)',
					border: '3px solid #4CAF50',
					width: '100%',
					maxWidth: '800px'
				}}>
					<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '10px', color: '#2c3e50'}}>
						✅ IMMEDIATE SOLUTION
					</div>
					<div style={{fontSize: '1.8rem', marginBottom: '8px', color: '#2c3e50', fontWeight: 600}}>
						Weekly zero-sales alerts
					</div>
					<div style={{fontSize: '1.6rem', color: '#2c3e50'}}>
						24h follow-up SLA required
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 8: 30-Day Action Plan (26s)
const Slide8: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const actionsOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const finalScale = spring({
		frame: frame - 200,
		fps,
		config: {
			damping: 12,
			stiffness: 150,
		},
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #d0f2f0 0%, #ffe8ee 100%)',
			color: '#2c3e50',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				{/* Header */}
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>🎯 30-DAY ACTION PLAN</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8, fontWeight: 600}}>Strategic Priorities</div>
				</div>

				{/* Action Items */}
				<div style={{
					opacity: actionsOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '12px',
					width: '100%',
					maxWidth: '800px'
				}}>
					{[
						{priority: '1. PROTECT CORE', action: 'Launch Appetizer save plan (promo refresh, ops audit)'},
						{priority: '2. FUEL WINNERS', action: 'Allocate media to Dessert, Japanese, ICEE Float'},
						{priority: '3. FIX AVAILABILITY', action: 'Implement zero-sales alerts & stock checks'},
						{priority: '4. OPTIMIZE PRICING', action: 'Convene pricing council; leverage combo insights'},
						{priority: '5. AUTOMATE REPORTING', action: 'Schedule monthly regeneration for leadership'},
					].map((item, index) => (
						<div key={index} style={{
							background: 'rgba(44,62,80,0.85)',
							padding: '15px 18px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '2px solid rgba(44,62,80,0.9)'
						}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px', color: '#4CAF50'}}>
								{item.priority}
							</div>
							<div style={{fontSize: '1.5rem', color: '#ffffff', lineHeight: 1.3}}>
								{item.action}
							</div>
						</div>
					))}
				</div>

				{/* Final Message */}
				<div style={{
					transform: `scale(${finalScale})`,
					background: 'rgba(44,62,80,0.9)',
					padding: '20px',
					borderRadius: '20px',
					backdropFilter: 'blur(10px)',
					border: '2px solid rgba(44,62,80,1)',
					marginTop: '10px',
					width: '100%',
					maxWidth: '800px'
				}}>
					<div style={{fontSize: '2rem', fontWeight: 900, textAlign: 'center', color: '#4CAF50'}}>
						🚀 EXECUTION STARTS NOW
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Main composition with narration timing
export const FBSalesBriefingWithNarration: React.FC = () => {
	const {fps} = useVideoConfig();

	// Audio durations from OpenAI TTS converted to frames at 30fps
	const slideDurations = [
		Math.ceil(12 * fps),    // Slide 1: 12 seconds (OpenAI TTS)
		Math.ceil(20 * fps),    // Slide 2: 20 seconds (19.8 + buffer)
		Math.ceil(18 * fps),    // Slide 3: 18 seconds (17.4 + buffer)
		Math.ceil(27 * fps),    // Slide 4: 27 seconds (26.472 + buffer)
		Math.ceil(26 * fps),    // Slide 5: 26 seconds (25.584 + buffer)
		Math.ceil(19 * fps),    // Slide 6: 19 seconds (18.768 + buffer)
		Math.ceil(18 * fps),    // Slide 7: 18 seconds (17.064 + buffer)
		Math.ceil(26 * fps),    // Slide 8: 26 seconds (25.536 + buffer)
	];

	let currentFrame = 0;

	return (
		<AbsoluteFill>
			{/* Slide 1: Title with Natural Audio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[0]}>
				<Slide1 />
				<Audio src={staticFile('audio/slide1_natural.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[0]}

			{/* Slide 2: Why This Matters with Natural Audio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[1]}>
				<Slide2 />
				<Audio src={staticFile('audio/slide2_natural.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[1]}

			{/* Slide 3: Financial Performance with Natural Audio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[2]}>
				<Slide3 />
				<Audio src={staticFile('audio/slide3_natural.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[2]}

			{/* Slide 4: Category Performance with Natural Audio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[3]}>
				<Slide4 />
				<Audio src={staticFile('audio/slide4_natural.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[3]}

			{/* Slide 5: Growth Leaders with Natural Audio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[4]}>
				<Slide5 />
				<Audio src={staticFile('audio/slide5_natural.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[4]}

			{/* Slide 6: Revenue Drags with Natural Audio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[5]}>
				<Slide6 />
				<Audio src={staticFile('audio/slide6_natural.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[5]}

			{/* Slide 7: Operational Issues with Natural Audio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[6]}>
				<Slide7 />
				<Audio src={staticFile('audio/slide7_natural.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[6]}

			{/* Slide 8: 30-Day Action Plan with Natural Audio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[7]}>
				<Slide8 />
				<Audio src={staticFile('audio/slide8_natural.mp3')} />
			</Sequence>
		</AbsoluteFill>
	);
};