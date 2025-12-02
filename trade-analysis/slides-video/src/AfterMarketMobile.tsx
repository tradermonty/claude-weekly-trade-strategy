import {
	useCurrentFrame,
	useVideoConfig,
	interpolate,
	AbsoluteFill,
	Sequence,
	spring,
	Easing,
} from 'remotion';

export const AfterMarketMobile: React.FC = () => {
	const frame = useCurrentFrame();
	const { fps } = useVideoConfig();

	// Market data extracted from the HTML report
	const marketData = {
		date: '2025-09-05',
		majorETFs: [
			{ symbol: 'SPY', price: '$647.24', change: '-0.29%', positive: false },
			{ symbol: 'QQQ', price: '$576.06', change: '+0.14%', positive: true },
			{ symbol: 'DIA', price: '$454.99', change: '-0.45%', positive: false },
			{ symbol: 'IWM', price: '$237.77', change: '+0.50%', positive: true },
			{ symbol: 'TLT', price: '$88.56', change: '+1.52%', positive: true },
			{ symbol: 'GLD', price: '$331.05', change: '+1.33%', positive: true },
		],
		volumeSurgeStocks: [
			{ symbol: '$KOD', name: 'Kodiak Gas Services', change: '+23.04%' },
			{ symbol: '$ZBIO', name: 'Zappus Bio Tech', change: '+20.79%' },
			{ symbol: '$GWRE', name: 'Guidewire Software', change: '+20.15%' },
			{ symbol: '$KRRO', name: 'Korro Bio', change: '+18.11%' },
			{ symbol: '$EYPT', name: 'EyePoint Pharma', change: '+17.93%' },
		],
		stats: {
			volumeSurgeTickers: 97,
			upTrendTickers: 881,
			avgRelativeVolume: '2.3x',
			avgPriceMove: '+6.9%',
		},
		sectors: [
			{ name: 'Basic Materials', performance: '+1.19%', positive: true },
			{ name: 'Real Estate', performance: '+1.05%', positive: true },
			{ name: 'Healthcare', performance: '+0.67%', positive: true },
			{ name: 'Communication', performance: '+0.51%', positive: true },
			{ name: 'Technology', performance: '+0.26%', positive: true },
			{ name: 'Consumer Cyclical', performance: '+0.14%', positive: true },
		],
	};

	// Slide timing configuration
	const slideDurations = [150, 210, 180, 150, 210, 120]; // frames for each slide
	const totalDuration = slideDurations.reduce((sum, duration) => sum + duration, 0);
	
	// Calculate slide start times
	const slideStarts = [0];
	for (let i = 0; i < slideDurations.length - 1; i++) {
		slideStarts.push(slideStarts[i] + slideDurations[i]);
	}

	// Common styles
	const backgroundGradient = 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)';
	
	return (
		<AbsoluteFill style={{ background: backgroundGradient }}>
			{/* Slide 1: Title Slide */}
			<Sequence from={slideStarts[0]} durationInFrames={slideDurations[0]}>
				<TitleSlide frame={frame - slideStarts[0]} fps={fps} data={marketData} />
			</Sequence>

			{/* Slide 2: Major ETF Performance */}
			<Sequence from={slideStarts[1]} durationInFrames={slideDurations[1]}>
				<ETFPerformanceSlide frame={frame - slideStarts[1]} fps={fps} data={marketData.majorETFs} />
			</Sequence>

			{/* Slide 3: Volume Surge Stocks */}
			<Sequence from={slideStarts[2]} durationInFrames={slideDurations[2]}>
				<VolumeSurgeSlide frame={frame - slideStarts[2]} fps={fps} data={marketData.volumeSurgeStocks} />
			</Sequence>

			{/* Slide 4: Market Statistics */}
			<Sequence from={slideStarts[3]} durationInFrames={slideDurations[3]}>
				<MarketStatsSlide frame={frame - slideStarts[3]} fps={fps} data={marketData.stats} />
			</Sequence>

			{/* Slide 5: Sector Performance */}
			<Sequence from={slideStarts[4]} durationInFrames={slideDurations[4]}>
				<SectorPerformanceSlide frame={frame - slideStarts[4]} fps={fps} data={marketData.sectors} />
			</Sequence>

			{/* Slide 6: Key Takeaways */}
			<Sequence from={slideStarts[5]} durationInFrames={slideDurations[5]}>
				<KeyTakeawaysSlide frame={frame - slideStarts[5]} fps={fps} />
			</Sequence>
		</AbsoluteFill>
	);
};

// Title Slide Component
const TitleSlide: React.FC<{ frame: number; fps: number; data: any }> = ({ frame, fps, data }) => {
	const slideIn = spring({
		frame,
		fps,
		config: { damping: 10, stiffness: 100, mass: 0.5 }
	});

	const fadeIn = interpolate(frame, [0, 30], [0, 1], { 
		extrapolateRight: 'clamp',
		easing: Easing.out(Easing.quad)
	});

	return (
		<AbsoluteFill style={{
			display: 'flex',
			flexDirection: 'column',
			justifyContent: 'center',
			alignItems: 'center',
			textAlign: 'center',
			padding: '60px 40px',
			opacity: fadeIn,
		}}>
			<div style={{
				transform: `scale(${slideIn}) translateY(${interpolate(slideIn, [0, 1], [50, 0])}px)`,
				background: 'rgba(255, 255, 255, 0.15)',
				backdropFilter: 'blur(10px)',
				borderRadius: '30px',
				padding: '60px 40px',
				boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)',
				border: '1px solid rgba(255, 255, 255, 0.2)',
			}}>
				<div style={{
					fontSize: '3.5rem',
					fontWeight: '800',
					color: '#ffffff',
					marginBottom: '30px',
					textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5)',
					lineHeight: '1.2',
				}}>
					🇺🇸 U.S. Stock Market
				</div>
				<div style={{
					fontSize: '2.8rem',
					fontWeight: '700',
					color: '#00ff88',
					marginBottom: '40px',
					textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5)',
				}}>
					After-Market Analysis
				</div>
				<div style={{
					fontSize: '2.2rem',
					fontWeight: '600',
					color: '#ffffff',
					opacity: 0.9,
					textShadow: '1px 1px 2px rgba(0, 0, 0, 0.5)',
				}}>
					📅 {data.date}
				</div>
			</div>
		</AbsoluteFill>
	);
};

// ETF Performance Slide Component
const ETFPerformanceSlide: React.FC<{ frame: number; fps: number; data: any[] }> = ({ frame, fps, data }) => {
	const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

	return (
		<AbsoluteFill style={{
			display: 'flex',
			flexDirection: 'column',
			justifyContent: 'flex-start',
			alignItems: 'center',
			padding: '80px 40px 40px',
			opacity: fadeIn,
		}}>
			{/* Title */}
			<div style={{
				fontSize: '3rem',
				fontWeight: '800',
				color: '#ffffff',
				textAlign: 'center',
				marginBottom: '60px',
				textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5)',
			}}>
				📊 Major ETF Performance
			</div>

			{/* ETF Grid */}
			<div style={{
				display: 'grid',
				gridTemplateColumns: 'repeat(2, 1fr)',
				gap: '30px',
				width: '100%',
				maxWidth: '900px',
			}}>
				{data.map((etf, index) => {
					const itemDelay = 30 + (index * 15);
					const itemFadeIn = interpolate(frame, [itemDelay, itemDelay + 20], [0, 1], { 
						extrapolateRight: 'clamp'
					});
					const itemSlideUp = interpolate(frame, [itemDelay, itemDelay + 20], [30, 0], { 
						extrapolateRight: 'clamp'
					});

					return (
						<div key={etf.symbol} style={{
							background: 'rgba(255, 255, 255, 0.15)',
							backdropFilter: 'blur(10px)',
							borderRadius: '20px',
							padding: '30px 20px',
							textAlign: 'center',
							border: '1px solid rgba(255, 255, 255, 0.2)',
							transform: `translateY(${itemSlideUp}px)`,
							opacity: itemFadeIn,
						}}>
							<div style={{
								fontSize: '2.5rem',
								fontWeight: '800',
								color: '#ffffff',
								marginBottom: '10px',
							}}>
								{etf.symbol}
							</div>
							<div style={{
								fontSize: '2rem',
								fontWeight: '600',
								color: '#ffffff',
								marginBottom: '10px',
							}}>
								{etf.price}
							</div>
							<div style={{
								fontSize: '2.2rem',
								fontWeight: '700',
								color: etf.positive ? '#00ff88' : '#ff6b6b',
								textShadow: `0 0 10px ${etf.positive ? 'rgba(0, 255, 136, 0.5)' : 'rgba(255, 107, 107, 0.5)'}`,
							}}>
								{etf.change}
							</div>
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

// Volume Surge Slide Component
const VolumeSurgeSlide: React.FC<{ frame: number; fps: number; data: any[] }> = ({ frame, fps, data }) => {
	const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

	return (
		<AbsoluteFill style={{
			display: 'flex',
			flexDirection: 'column',
			justifyContent: 'flex-start',
			alignItems: 'center',
			padding: '80px 40px 40px',
			opacity: fadeIn,
		}}>
			{/* Title */}
			<div style={{
				fontSize: '3rem',
				fontWeight: '800',
				color: '#ffffff',
				textAlign: 'center',
				marginBottom: '60px',
				textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5)',
			}}>
				🔥 Volume Surge Leaders
			</div>

			{/* Stocks List */}
			<div style={{
				width: '100%',
				maxWidth: '900px',
				display: 'flex',
				flexDirection: 'column',
				gap: '25px',
			}}>
				{data.map((stock, index) => {
					const itemDelay = 30 + (index * 20);
					const itemFadeIn = interpolate(frame, [itemDelay, itemDelay + 25], [0, 1], { 
						extrapolateRight: 'clamp'
					});
					const itemSlideIn = interpolate(frame, [itemDelay, itemDelay + 25], [-50, 0], { 
						extrapolateRight: 'clamp'
					});

					return (
						<div key={stock.symbol} style={{
							background: 'rgba(255, 255, 255, 0.15)',
							backdropFilter: 'blur(10px)',
							borderRadius: '20px',
							padding: '25px 30px',
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center',
							border: '1px solid rgba(255, 255, 255, 0.2)',
							transform: `translateX(${itemSlideIn}px)`,
							opacity: itemFadeIn,
						}}>
							<div>
								<div style={{
									fontSize: '2.2rem',
									fontWeight: '800',
									color: '#ffffff',
									marginBottom: '5px',
								}}>
									{stock.symbol}
								</div>
								<div style={{
									fontSize: '1.6rem',
									fontWeight: '500',
									color: '#ffffff',
									opacity: 0.8,
								}}>
									{stock.name}
								</div>
							</div>
							<div style={{
								fontSize: '2.5rem',
								fontWeight: '800',
								color: '#00ff88',
								textShadow: '0 0 10px rgba(0, 255, 136, 0.5)',
							}}>
								{stock.change}
							</div>
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

// Market Stats Slide Component
const MarketStatsSlide: React.FC<{ frame: number; fps: number; data: any }> = ({ frame, fps, data }) => {
	const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

	return (
		<AbsoluteFill style={{
			display: 'flex',
			flexDirection: 'column',
			justifyContent: 'center',
			alignItems: 'center',
			padding: '60px 40px',
			opacity: fadeIn,
		}}>
			{/* Title */}
			<div style={{
				fontSize: '3rem',
				fontWeight: '800',
				color: '#ffffff',
				textAlign: 'center',
				marginBottom: '80px',
				textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5)',
			}}>
				📈 Market Statistics
			</div>

			{/* Stats Grid */}
			<div style={{
				display: 'grid',
				gridTemplateColumns: 'repeat(2, 1fr)',
				gap: '40px',
				width: '100%',
				maxWidth: '800px',
			}}>
				{Object.entries(data).map(([key, value], index) => {
					const itemDelay = 30 + (index * 20);
					const itemFadeIn = interpolate(frame, [itemDelay, itemDelay + 25], [0, 1], { 
						extrapolateRight: 'clamp'
					});
					const itemScale = spring({
						frame: Math.max(0, frame - itemDelay),
						fps,
						config: { damping: 8, stiffness: 120 }
					});

					const labels: { [key: string]: string } = {
						volumeSurgeTickers: 'Volume Surge Tickers',
						upTrendTickers: 'Up-Trend Tickers',
						avgRelativeVolume: 'Avg Relative Volume',
						avgPriceMove: 'Avg Price Move',
					};

					return (
						<div key={key} style={{
							background: 'rgba(255, 255, 255, 0.15)',
							backdropFilter: 'blur(10px)',
							borderRadius: '25px',
							padding: '40px 30px',
							textAlign: 'center',
							border: '1px solid rgba(255, 255, 255, 0.2)',
							transform: `scale(${itemScale})`,
							opacity: itemFadeIn,
						}}>
							<div style={{
								fontSize: '3.5rem',
								fontWeight: '900',
								color: '#00ff88',
								marginBottom: '15px',
								textShadow: '0 0 20px rgba(0, 255, 136, 0.5)',
							}}>
								{value}
							</div>
							<div style={{
								fontSize: '1.8rem',
								fontWeight: '600',
								color: '#ffffff',
								lineHeight: '1.3',
							}}>
								{labels[key]}
							</div>
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

// Sector Performance Slide Component
const SectorPerformanceSlide: React.FC<{ frame: number; fps: number; data: any[] }> = ({ frame, fps, data }) => {
	const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

	return (
		<AbsoluteFill style={{
			display: 'flex',
			flexDirection: 'column',
			justifyContent: 'flex-start',
			alignItems: 'center',
			padding: '80px 40px 40px',
			opacity: fadeIn,
		}}>
			{/* Title */}
			<div style={{
				fontSize: '3rem',
				fontWeight: '800',
				color: '#ffffff',
				textAlign: 'center',
				marginBottom: '60px',
				textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5)',
			}}>
				🏢 Top Sector Performance
			</div>

			{/* Sectors List */}
			<div style={{
				width: '100%',
				maxWidth: '900px',
				display: 'flex',
				flexDirection: 'column',
				gap: '25px',
			}}>
				{data.map((sector, index) => {
					const itemDelay = 30 + (index * 15);
					const itemFadeIn = interpolate(frame, [itemDelay, itemDelay + 20], [0, 1], { 
						extrapolateRight: 'clamp'
					});
					const itemSlideIn = interpolate(frame, [itemDelay, itemDelay + 20], [30, 0], { 
						extrapolateRight: 'clamp'
					});

					return (
						<div key={sector.name} style={{
							background: 'rgba(255, 255, 255, 0.15)',
							backdropFilter: 'blur(10px)',
							borderRadius: '18px',
							padding: '25px 35px',
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center',
							border: '1px solid rgba(255, 255, 255, 0.2)',
							transform: `translateY(${itemSlideIn}px)`,
							opacity: itemFadeIn,
						}}>
							<div style={{
								fontSize: '2rem',
								fontWeight: '600',
								color: '#ffffff',
							}}>
								{sector.name}
							</div>
							<div style={{
								fontSize: '2.5rem',
								fontWeight: '800',
								color: sector.positive ? '#00ff88' : '#ff6b6b',
								textShadow: `0 0 10px ${sector.positive ? 'rgba(0, 255, 136, 0.5)' : 'rgba(255, 107, 107, 0.5)'}`,
							}}>
								{sector.performance}
							</div>
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

// Key Takeaways Slide Component
const KeyTakeawaysSlide: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
	const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

	const takeaways = [
		'📊 Mixed market with safe haven flows',
		'🔥 97 volume surge stocks detected',
		'💰 Bonds & Gold outperformed (+1.5%)',
		'🏢 Materials & Real Estate led sectors',
	];

	return (
		<AbsoluteFill style={{
			display: 'flex',
			flexDirection: 'column',
			justifyContent: 'center',
			alignItems: 'center',
			padding: '60px 40px',
			opacity: fadeIn,
			textAlign: 'center',
		}}>
			{/* Title */}
			<div style={{
				fontSize: '3.2rem',
				fontWeight: '800',
				color: '#ffffff',
				marginBottom: '80px',
				textShadow: '2px 2px 4px rgba(0, 0, 0, 0.5)',
			}}>
				🔍 Key Takeaways
			</div>

			{/* Takeaways */}
			<div style={{
				width: '100%',
				maxWidth: '900px',
				display: 'flex',
				flexDirection: 'column',
				gap: '30px',
			}}>
				{takeaways.map((takeaway, index) => {
					const itemDelay = 30 + (index * 20);
					const itemFadeIn = interpolate(frame, [itemDelay, itemDelay + 25], [0, 1], { 
						extrapolateRight: 'clamp'
					});
					const itemSlideIn = interpolate(frame, [itemDelay, itemDelay + 25], [-30, 0], { 
						extrapolateRight: 'clamp'
					});

					return (
						<div key={index} style={{
							background: 'rgba(255, 255, 255, 0.15)',
							backdropFilter: 'blur(10px)',
							borderRadius: '20px',
							padding: '30px 40px',
							fontSize: '2.2rem',
							fontWeight: '600',
							color: '#ffffff',
							textAlign: 'left',
							border: '1px solid rgba(255, 255, 255, 0.2)',
							transform: `translateX(${itemSlideIn}px)`,
							opacity: itemFadeIn,
						}}>
							{takeaway}
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};