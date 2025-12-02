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

// Slide 1: Title Slide
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

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '30px', width: '100%'}}>
				<div style={{transform: `scale(${titleScale})`, textAlign: 'center'}}>
					<div style={{fontSize: '2.2rem', opacity: 0.9, marginBottom: '10px'}}>📈 米国株投資戦略</div>
					<h1 style={{fontSize: '3.8rem', marginBottom: '15px', fontWeight: 900, lineHeight: 1.1, textShadow: '2px 2px 4px rgba(0,0,0,0.3)'}}>2025年9月22日週</h1>
				</div>

				<div style={{opacity: subtitleOpacity, textAlign: 'center'}}>
					<h2 style={{fontSize: '2.6rem', fontWeight: 700, marginBottom: '20px', lineHeight: 1.1}}>低ボラティリティ×高値更新</h2>
					<div style={{backgroundColor: 'rgba(255,255,255,0.2)', padding: '12px 20px', borderRadius: '25px', fontSize: '1.8rem', fontWeight: 600}}>
						選別的リスクオン相場
					</div>
				</div>

				<div style={{
					opacity: subtitleOpacity,
					fontSize: '1.6rem',
					backgroundColor: 'rgba(255,255,255,0.15)',
					padding: '15px 25px',
					borderRadius: '15px',
					marginTop: '20px'
				}}>
					SPX 6,659 / NDX 24.6k / 10年債 4.12-4.36%
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 2: Key Points (3-line summary)
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
			background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>📊 今週のポイント</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>3行まとめ</div>
				</div>

				<div style={{
					opacity: pointsOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '20px',
					width: '100%',
					maxWidth: '900px'
				}}>
					<div style={{background: 'rgba(76,175,80,0.3)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '3px solid #4CAF50'}}>
						<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '8px', color: '#4CAF50'}}>📈 主要指数は週足で続伸</div>
						<div style={{fontSize: '1.7rem', marginBottom: '5px'}}>S&P500 ≈ 6,659、NASDAQ100 ≈ 24,600</div>
						<div style={{fontSize: '1.7rem'}}>RUTは2,480の壁を前に足踏み</div>
					</div>

					<div style={{background: 'rgba(255,193,7,0.25)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid #FFC107'}}>
						<div style={{fontSize: '2rem', fontWeight: 700, marginBottom: '8px', color: '#FFC107'}}>🧭 金利4.13%・VIX15台</div>
						<div style={{fontSize: '1.6rem', marginBottom: '5px'}}>低ボラのリスクオン環境は維持</div>
						<div style={{fontSize: '1.6rem'}}>10年債は4.12%サポート上で反発気味</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.2)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px'}}>🥇 コモディティはコントラスト鮮明</div>
						<div style={{fontSize: '1.6rem'}}>金3,706ドル高値更新・ウラン+17%・原油62ドル台弱含み</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 3: Market Summary
const Slide3: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const dataOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>📊 市況サマリー</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>重要レベル監視</div>
				</div>

				<div style={{
					opacity: dataOpacity,
					display: 'grid',
					gridTemplateColumns: '1fr 1fr',
					gap: '15px',
					width: '100%',
					maxWidth: '850px'
				}}>
					<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.4)'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px', color: '#FFE082'}}>🏛️ 米10年債利回り</div>
						<div style={{fontSize: '2.2rem', fontWeight: 900, color: '#FFF'}}>4.13%</div>
						<div style={{fontSize: '1.4rem', opacity: 0.9}}>サポート: 4.12% / 天井: 4.36%</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.4)'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px', color: '#4FC3F7'}}>📉 VIX</div>
						<div style={{fontSize: '2.2rem', fontWeight: 900, color: '#FFF'}}>15.46</div>
						<div style={{fontSize: '1.4rem', opacity: 0.9}}>低位安定・17/20/23が切替点</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.4)'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px', color: '#81C784'}}>📈 Breadth</div>
						<div style={{fontSize: '2.2rem', fontWeight: 900, color: '#FFF'}}>30%台</div>
						<div style={{fontSize: '1.4rem', opacity: 0.9}}>40%未満で押し目中心</div>
					</div>

					<div style={{background: 'rgba(255,255,255,0.25)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,255,255,0.4)'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px', color: '#FFB74D'}}>🥇 Gold</div>
						<div style={{fontSize: '2.2rem', fontWeight: 900, color: '#FFF'}}>3,706</div>
						<div style={{fontSize: '1.4rem', opacity: 0.9}}>3,538ブレイクで青天井</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 4: Sector Performance
const Slide4: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const topPerformersOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const bottomPerformersOpacity = interpolate(frame, [120, 160], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%'}}>
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '2.8rem', marginBottom: '8px', fontWeight: 900}}>📊 セクター・コモディティ</h1>
					<div style={{fontSize: '1.5rem', opacity: 0.8}}>1週間パフォーマンス</div>
				</div>

				<div style={{
					opacity: topPerformersOpacity,
					width: '100%',
					maxWidth: '900px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '12px', textAlign: 'center', color: '#4CAF50'}}>🚀 トップセクター</div>
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '20px'}}>
						<div style={{background: 'rgba(76,175,80,0.3)', padding: '18px 12px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '3px solid #4CAF50'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>通信</div>
							<div style={{fontSize: '2.2rem', color: '#4CAF50', fontWeight: 900}}>+3.26%</div>
						</div>
						<div style={{background: 'rgba(76,175,80,0.3)', padding: '18px 12px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '3px solid #4CAF50'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>テック</div>
							<div style={{fontSize: '2.2rem', color: '#4CAF50', fontWeight: 900}}>+2.51%</div>
						</div>
						<div style={{background: 'rgba(76,175,80,0.3)', padding: '18px 12px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '3px solid #4CAF50'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>ウラン</div>
							<div style={{fontSize: '2.2rem', color: '#4CAF50', fontWeight: 900}}>+12.8%</div>
						</div>
					</div>
				</div>

				<div style={{
					opacity: bottomPerformersOpacity,
					width: '100%',
					maxWidth: '900px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '12px', textAlign: 'center', color: '#ff6b6b'}}>📉 弱含みセクター</div>
					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px'}}>
						<div style={{background: 'rgba(255,107,107,0.25)', padding: '18px 12px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,107,107,0.4)'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>不動産</div>
							<div style={{fontSize: '2rem', color: '#ff6b6b', fontWeight: 800}}>-1.50%</div>
						</div>
						<div style={{background: 'rgba(255,107,107,0.25)', padding: '18px 12px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,107,107,0.4)'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>生活必需</div>
							<div style={{fontSize: '2rem', color: '#ff6b6b', fontWeight: 800}}>-1.41%</div>
						</div>
						<div style={{background: 'rgba(255,107,107,0.25)', padding: '18px 12px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid rgba(255,107,107,0.4)'}}>
							<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '5px'}}>原油</div>
							<div style={{fontSize: '2rem', color: '#ff6b6b', fontWeight: 800}}>62ドル台</div>
						</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 5: Strategy & Scenarios
const Slide5: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const strategyOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
			color: '#2c3e50',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900, color: '#2c3e50'}}>🎯 全体戦略</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8, fontWeight: 600, color: '#2c3e50'}}>やや強気（攻め6：守り4）</div>
				</div>

				<div style={{
					opacity: strategyOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '20px',
					width: '100%',
					maxWidth: '900px'
				}}>
					<div style={{background: 'rgba(44,62,80,0.1)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '3px solid #2c3e50'}}>
						<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '15px', color: '#2c3e50'}}>
							📊 三点スイッチ
						</div>
						<div style={{fontSize: '1.7rem', marginBottom: '8px', color: '#2c3e50', fontWeight: 600}}>
							• 10年債: 4.12% / 4.36% / 4.50%
						</div>
						<div style={{fontSize: '1.7rem', marginBottom: '8px', color: '#2c3e50', fontWeight: 600}}>
							• VIX: 17 / 20 / 23
						</div>
						<div style={{fontSize: '1.7rem', color: '#2c3e50', fontWeight: 600}}>
							• Breadth: 0.40（拡大ラリー閾値）
						</div>
					</div>

					<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px'}}>
						<div style={{background: 'rgba(76,175,80,0.2)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid #4CAF50'}}>
							<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px', color: '#2c3e50'}}>ベースシナリオ</div>
							<div style={{fontSize: '1.5rem', color: '#2c3e50', fontWeight: 600}}>指数コア70%まで</div>
							<div style={{fontSize: '1.4rem', color: '#2c3e50'}}>押し目=8EMA/20EMA</div>
						</div>
						<div style={{background: 'rgba(255,193,7,0.2)', padding: '18px', borderRadius: '15px', backdropFilter: 'blur(10px)', border: '2px solid #FFC107'}}>
							<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px', color: '#2c3e50'}}>リスクオフ</div>
							<div style={{fontSize: '1.5rem', color: '#2c3e50', fontWeight: 600}}>ロット半減・ヘッジ導入</div>
							<div style={{fontSize: '1.4rem', color: '#2c3e50'}}>GLD/SH追加</div>
						</div>
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 6: Asset Allocation
const Slide6: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const assetsOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
			color: '#2c3e50',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900, color: '#2c3e50'}}>💼 アセット別具体策</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8, fontWeight: 600, color: '#2c3e50'}}>週足ベース</div>
				</div>

				<div style={{
					opacity: assetsOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '15px',
					width: '100%',
					maxWidth: '900px'
				}}>
					{[
						{asset: 'S&P500', level: '6,540±40', action: '押し目拾い', stop: '6,500割れ撤退'},
						{asset: 'NASDAQ100', level: '24.1k付近', action: '戻り待ち分割IN', stop: '直近安値-1.5%'},
						{asset: 'Russell2000', level: '2,480実体抜け', action: '1/3→追加', stop: '週足基準'},
						{asset: 'ゴールド', level: '3,538上維持', action: 'ヘッジ兼用5%', stop: '3,640押し目拾い'},
						{asset: 'ウラン', level: '45±1押し目', action: '5週線トレーリング', stop: '週陰転で半益'},
						{asset: '原油', level: 'WTI<65中立', action: '65-70戻りで短期', stop: '72超で強気'},
					].map((item, index) => (
						<div key={index} style={{
							background: 'rgba(44,62,80,0.1)',
							padding: '15px 18px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '2px solid rgba(44,62,80,0.3)',
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center'
						}}>
							<div>
								<div style={{fontSize: '1.6rem', fontWeight: 700, marginBottom: '3px', color: '#2c3e50'}}>{item.asset}</div>
								<div style={{fontSize: '1.3rem', color: '#2c3e50', opacity: 0.8}}>{item.level}</div>
							</div>
							<div style={{textAlign: 'right'}}>
								<div style={{fontSize: '1.4rem', color: '#4CAF50', fontWeight: 600}}>{item.action}</div>
								<div style={{fontSize: '1.2rem', color: '#ff6b6b', opacity: 0.9}}>{item.stop}</div>
							</div>
						</div>
					))}
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 7: Portfolio Allocation
const Slide7: React.FC = () => {
	const frame = useCurrentFrame();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const portfolioOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>📊 セクター配分</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8}}>上限=口座の80%</div>
				</div>

				<div style={{
					opacity: portfolioOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '15px',
					width: '100%',
					maxWidth: '850px'
				}}>
					{[
						{category: 'コア指数', allocation: '45%', detail: 'VOO 25% + QQQ 20%', condition: '8EMA割れで縮小'},
						{category: 'テック/AI', allocation: '12%', detail: 'MSFT/NVDA/XLK', condition: '押し目限定'},
						{category: '素材', allocation: '10%', detail: 'COPX/FCX', condition: '銅4.708上で増加'},
						{category: 'ウラン', allocation: '8%', detail: 'URA/CCJ', condition: '週陰転で半益'},
						{category: '金', allocation: '5%', detail: 'GLD/GDX', condition: 'VIX>20で増枠'},
						{category: 'キャッシュ&ヘッジ', allocation: '20%', detail: 'BIL/SH', condition: 'VIX>23でSH導入'},
					].map((item, index) => (
						<div key={index} style={{
							background: 'rgba(255,255,255,0.2)',
							padding: '16px 20px',
							borderRadius: '15px',
							backdropFilter: 'blur(10px)',
							border: '2px solid rgba(255,255,255,0.3)',
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center'
						}}>
							<div>
								<div style={{fontSize: '1.7rem', fontWeight: 700, marginBottom: '4px'}}>{item.category}</div>
								<div style={{fontSize: '1.4rem', opacity: 0.9}}>{item.detail}</div>
							</div>
							<div style={{textAlign: 'right'}}>
								<div style={{fontSize: '2.2rem', color: '#4CAF50', fontWeight: 900}}>{item.allocation}</div>
								<div style={{fontSize: '1.2rem', opacity: 0.8}}>{item.condition}</div>
							</div>
						</div>
					))}
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Slide 8: Risk Management & Summary
const Slide8: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	const titleOpacity = interpolate(frame, [0, 40], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const riskOpacity = interpolate(frame, [40, 80], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const finalScale = spring({
		frame: frame - 120,
		fps,
		config: {
			damping: 12,
			stiffness: 150,
		},
	});

	return (
		<AbsoluteFill style={{
			background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
			...slideStyle
		}}>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '25px', width: '100%'}}>
				<div style={{opacity: titleOpacity, textAlign: 'center'}}>
					<h1 style={{fontSize: '3rem', marginBottom: '10px', fontWeight: 900}}>⚠️ リスク管理</h1>
					<div style={{fontSize: '1.6rem', opacity: 0.8, fontWeight: 600}}>必ず実装</div>
				</div>

				<div style={{
					opacity: riskOpacity,
					display: 'flex',
					flexDirection: 'column',
					gap: '20px',
					width: '100%',
					maxWidth: '850px'
				}}>
					<div style={{background: 'rgba(255,107,107,0.25)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '3px solid #ff6b6b'}}>
						<div style={{fontSize: '2rem', fontWeight: 800, marginBottom: '15px', color: '#ff6b6b'}}>
							🛡️ 基本原則
						</div>
						<div style={{fontSize: '1.7rem', marginBottom: '8px', fontWeight: 600}}>• 1銘柄リスク ≤ 0.5%</div>
						<div style={{fontSize: '1.7rem', marginBottom: '8px', fontWeight: 600}}>• ポート全体で1%以内</div>
						<div style={{fontSize: '1.7rem', fontWeight: 600}}>• VIX&gt;23 or 10Y&gt;4.50で新規建て停止</div>
					</div>

					<div style={{background: 'rgba(76,175,80,0.3)', padding: '20px', borderRadius: '18px', backdropFilter: 'blur(10px)', border: '2px solid #4CAF50'}}>
						<div style={{fontSize: '1.8rem', fontWeight: 700, marginBottom: '10px', color: '#4CAF50'}}>
							📈 まとめ：選別的リスクオン継続
						</div>
						<div style={{fontSize: '1.6rem', marginBottom: '8px'}}>• テーマ：メガテック＋金＋ウラン</div>
						<div style={{fontSize: '1.6rem', marginBottom: '8px'}}>• 戦術：押し目中心、追いは浅く</div>
						<div style={{fontSize: '1.6rem'}}>• 三点スイッチで機械的配分変更</div>
					</div>
				</div>

				<div style={{
					transform: `scale(${finalScale})`,
					background: 'rgba(255,255,255,0.2)',
					padding: '20px',
					borderRadius: '20px',
					backdropFilter: 'blur(10px)',
					border: '2px solid rgba(255,255,255,0.3)',
					marginTop: '15px'
				}}>
					<div style={{fontSize: '1.8rem', fontWeight: 900, textAlign: 'center'}}>
						投資は自己責任で 📋
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

// Main composition with Japanese narration timing
export const USStockStrategy20250922: React.FC = () => {
	const {fps} = useVideoConfig();

	// Actual durations based on OpenAI TTS Japanese audio
	const slideDurations = [
		Math.ceil(27 * fps),    // Slide 1: Title - 26.328 seconds + buffer
		Math.ceil(54 * fps),    // Slide 2: Key Points - 53.016 seconds + buffer
		Math.ceil(46 * fps),    // Slide 3: Market Summary - 45.144 seconds + buffer
		Math.ceil(48 * fps),    // Slide 4: Sector Performance - 47.640 seconds + buffer
		Math.ceil(45 * fps),    // Slide 5: Strategy - 44.640 seconds + buffer
		Math.ceil(71 * fps),    // Slide 6: Asset Allocation - 70.416 seconds + buffer
		Math.ceil(49 * fps),    // Slide 7: Portfolio - 48.744 seconds + buffer
		Math.ceil(49 * fps),    // Slide 8: Risk Management - 48.264 seconds + buffer
	];

	let currentFrame = 0;

	return (
		<AbsoluteFill>
			{/* Slide 1: Title */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[0]}>
				<Slide1 />
				<Audio src={staticFile('audio/us_strategy_slide1.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[0]}

			{/* Slide 2: Key Points */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[1]}>
				<Slide2 />
				<Audio src={staticFile('audio/us_strategy_slide2.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[1]}

			{/* Slide 3: Market Summary */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[2]}>
				<Slide3 />
				<Audio src={staticFile('audio/us_strategy_slide3.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[2]}

			{/* Slide 4: Sector Performance */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[3]}>
				<Slide4 />
				<Audio src={staticFile('audio/us_strategy_slide4.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[3]}

			{/* Slide 5: Strategy */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[4]}>
				<Slide5 />
				<Audio src={staticFile('audio/us_strategy_slide5.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[4]}

			{/* Slide 6: Asset Allocation */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[5]}>
				<Slide6 />
				<Audio src={staticFile('audio/us_strategy_slide6.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[5]}

			{/* Slide 7: Portfolio */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[6]}>
				<Slide7 />
				<Audio src={staticFile('audio/us_strategy_slide7.mp3')} />
			</Sequence>
			{currentFrame += slideDurations[6]}

			{/* Slide 8: Risk Management */}
			<Sequence from={currentFrame} durationInFrames={slideDurations[7]}>
				<Slide8 />
				<Audio src={staticFile('audio/us_strategy_slide8.mp3')} />
			</Sequence>
		</AbsoluteFill>
	);
};