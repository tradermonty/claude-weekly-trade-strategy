import {AbsoluteFill, Audio, Sequence, useCurrentFrame, useVideoConfig, interpolate, Easing, staticFile} from 'remotion';
import React from 'react';
import earningsNarration from './earnings-trade-narration-with-durations.json';

export const EarningsTradeSquare: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  const slideDurations = [
    Math.ceil((16.42 + 1) * fps), // Slide 1: ~17.4s (~522 frames)
    Math.ceil((14.71 + 1) * fps), // Slide 2: ~15.7s (~471 frames)  
    Math.ceil((19.56 + 1) * fps), // Slide 3: ~20.6s (~617 frames)
    Math.ceil((16.06 + 1) * fps), // Slide 4: ~17.1s (~512 frames)
    Math.ceil((16.82 + 1) * fps), // Slide 5: ~17.8s (~535 frames)
    Math.ceil((22.68 + 1) * fps), // Slide 6: ~23.7s (~710 frames)
  ];
  
  // Calculate cumulative frames for each slide
  const cumulativeFrames = [0];
  for (let i = 0; i < slideDurations.length; i++) {
    cumulativeFrames.push(cumulativeFrames[i] + slideDurations[i]);
  }
  
  // Determine current slide based on frame
  let currentSlide = 0;
  for (let i = 0; i < slideDurations.length; i++) {
    if (frame >= cumulativeFrames[i] && frame < cumulativeFrames[i + 1]) {
      currentSlide = i;
      break;
    }
  }
  
  const slideFrame = frame - cumulativeFrames[currentSlide];
  
  const slideOpacity = interpolate(
    slideFrame,
    [0, 15, slideDurations[currentSlide] - 15, slideDurations[currentSlide]],
    [0, 1, 1, 0],
    {
      easing: Easing.inOut(Easing.quad),
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  );

  const backgroundGradient = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';

  const slideData = earningsNarration.slides[currentSlide];

  return (
    <AbsoluteFill style={{
      background: backgroundGradient,
      fontFamily: "'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif",
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '40px',
      opacity: slideOpacity,
    }}>
      {/* Audio Components - Each slide has its own audio in a Sequence */}
      <Sequence from={cumulativeFrames[0]} durationInFrames={slideDurations[0]}>
        <Audio src={staticFile('audio/earnings-slide-1-narration.mp3')} />
      </Sequence>
      <Sequence from={cumulativeFrames[1]} durationInFrames={slideDurations[1]}>
        <Audio src={staticFile('audio/earnings-slide-2-narration.mp3')} />
      </Sequence>
      <Sequence from={cumulativeFrames[2]} durationInFrames={slideDurations[2]}>
        <Audio src={staticFile('audio/earnings-slide-3-narration.mp3')} />
      </Sequence>
      <Sequence from={cumulativeFrames[3]} durationInFrames={slideDurations[3]}>
        <Audio src={staticFile('audio/earnings-slide-4-narration.mp3')} />
      </Sequence>
      <Sequence from={cumulativeFrames[4]} durationInFrames={slideDurations[4]}>
        <Audio src={staticFile('audio/earnings-slide-5-narration.mp3')} />
      </Sequence>
      <Sequence from={cumulativeFrames[5]} durationInFrames={slideDurations[5]}>
        <Audio src={staticFile('audio/earnings-slide-6-narration.mp3')} />
      </Sequence>

      {/* Slide Content */}
      {currentSlide === 0 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          maxWidth: '900px',
        }}>
          <h1 style={{
            fontSize: '3.2rem',
            fontWeight: 'bold',
            marginBottom: '25px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            lineHeight: '1.2',
          }}>
            {slideData.title}
          </h1>
          <div style={{
            fontSize: '1.5rem',
            marginBottom: '35px',
            opacity: 0.9,
            fontWeight: '300',
          }}>
            {slideData.subtitle}
          </div>
          <div style={{
            background: 'rgba(255,255,255,0.15)',
            padding: '20px',
            borderRadius: '15px',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.2)',
            fontSize: '1.1rem',
            lineHeight: '1.5',
          }}>
            9銘柄の詳細分析と<br/>バックテストスコアによる投資判断
          </div>
        </div>
      )}

      {currentSlide === 1 && (
        <div style={{
          background: 'white',
          borderRadius: '20px',
          padding: '40px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '850px',
          width: '100%',
        }}>
          <h1 style={{
            fontSize: '2.5rem',
            color: '#2c3e50',
            marginBottom: '35px',
            textAlign: 'center',
            fontWeight: 'bold',
          }}>
            {slideData.title}
          </h1>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '20px',
            marginTop: '20px',
          }}>
            {[
              { label: '分析銘柄数', value: slideData.data.analyzed, color: '#3498db' },
              { label: 'Aグレード', value: slideData.data.a_grade, color: '#27ae60' },
              { label: 'Bグレード', value: slideData.data.b_grade, color: '#3498db' },
              { label: '平均EPS予想超過', value: slideData.data.avg_eps_surprise, color: '#f39c12' },
            ].map((item, index) => (
              <div key={index} style={{
                background: '#f8f9fa',
                padding: '20px',
                borderRadius: '12px',
                textAlign: 'center',
                border: `3px solid ${item.color}`,
              }}>
                <div style={{
                  fontSize: '2.5rem',
                  fontWeight: 'bold',
                  color: item.color,
                  marginBottom: '8px',
                }}>
                  {item.value}
                </div>
                <div style={{
                  fontSize: '1rem',
                  color: '#2c3e50',
                  fontWeight: '500',
                }}>
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {currentSlide === 2 && (
        <div style={{
          background: 'linear-gradient(135deg, #27ae60, #2ecc71)',
          borderRadius: '20px',
          padding: '35px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '850px',
          width: '100%',
          color: 'white',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '25px',
          }}>
            <h1 style={{
              fontSize: '2.5rem',
              fontWeight: 'bold',
              margin: 0,
            }}>
              {slideData.data.symbol}
            </h1>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '12px 20px',
              borderRadius: '50px',
              fontSize: '1.2rem',
              fontWeight: 'bold',
            }}>
              A-Grade ★★★★★
            </div>
          </div>
          
          <div style={{
            fontSize: '1.3rem',
            marginBottom: '30px',
            opacity: 0.9,
          }}>
            {slideData.data.name}
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '15px',
          }}>
            {[
              { label: '現在株価', value: slideData.data.price },
              { label: '1日パフォーマンス', value: slideData.data.performance },
              { label: '総合スコア', value: slideData.data.score },
              { label: '成功確率', value: slideData.data.probability },
            ].map((item, index) => (
              <div key={index} style={{
                background: 'rgba(255,255,255,0.15)',
                padding: '18px',
                borderRadius: '12px',
                textAlign: 'center',
                backdropFilter: 'blur(5px)',
              }}>
                <div style={{
                  fontSize: '1.8rem',
                  fontWeight: 'bold',
                  marginBottom: '5px',
                }}>
                  {item.value}
                </div>
                <div style={{
                  fontSize: '0.9rem',
                  opacity: 0.8,
                }}>
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {currentSlide === 3 && (
        <div style={{
          background: 'linear-gradient(135deg, #27ae60, #2ecc71)',
          borderRadius: '20px',
          padding: '35px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '850px',
          width: '100%',
          color: 'white',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '25px',
          }}>
            <h1 style={{
              fontSize: '2.5rem',
              fontWeight: 'bold',
              margin: 0,
            }}>
              {slideData.data.symbol}
            </h1>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '12px 20px',
              borderRadius: '50px',
              fontSize: '1.2rem',
              fontWeight: 'bold',
            }}>
              A-Grade ★★★★★
            </div>
          </div>
          
          <div style={{
            fontSize: '1.3rem',
            marginBottom: '30px',
            opacity: 0.9,
          }}>
            {slideData.data.name}
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '15px',
          }}>
            {[
              { label: '現在株価', value: slideData.data.price },
              { label: '1日パフォーマンス', value: slideData.data.performance },
              { label: 'EPS予想超過', value: slideData.data.eps_surprise },
              { label: '総合スコア', value: slideData.data.score },
            ].map((item, index) => (
              <div key={index} style={{
                background: 'rgba(255,255,255,0.15)',
                padding: '18px',
                borderRadius: '12px',
                textAlign: 'center',
                backdropFilter: 'blur(5px)',
              }}>
                <div style={{
                  fontSize: '1.8rem',
                  fontWeight: 'bold',
                  marginBottom: '5px',
                }}>
                  {item.value}
                </div>
                <div style={{
                  fontSize: '0.9rem',
                  opacity: 0.8,
                }}>
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {currentSlide === 4 && (
        <div style={{
          background: 'white',
          borderRadius: '20px',
          padding: '35px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '850px',
          width: '100%',
        }}>
          <h1 style={{
            fontSize: '2.5rem',
            color: '#2c3e50',
            marginBottom: '30px',
            textAlign: 'center',
            fontWeight: 'bold',
          }}>
            {slideData.title}
          </h1>
          
          <div style={{
            display: 'grid',
            gap: '15px',
          }}>
            {[
              { symbol: 'BRZE', name: 'Braze Inc', performance: '+18.66%', highlight: '403% EPS超過' },
              { symbol: 'GWRE', name: 'Guidewire', performance: '+13.89%', highlight: 'ARR $1B突破' },
              { symbol: 'IOT', name: 'Samsara', performance: '+12.42%', highlight: 'AI需要拡大' },
            ].map((stock, index) => (
              <div key={index} style={{
                background: 'linear-gradient(135deg, #3498db, #5dade2)',
                padding: '20px',
                borderRadius: '12px',
                color: 'white',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>{stock.symbol}</div>
                  <div style={{ fontSize: '1rem', opacity: 0.9 }}>{stock.name}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>{stock.performance}</div>
                  <div style={{ fontSize: '0.9rem', opacity: 0.8 }}>{stock.highlight}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {currentSlide === 5 && (
        <div style={{
          background: 'white',
          borderRadius: '20px',
          padding: '35px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '850px',
          width: '100%',
          textAlign: 'center',
        }}>
          <h1 style={{
            fontSize: '2.5rem',
            color: '#2c3e50',
            marginBottom: '30px',
            fontWeight: 'bold',
          }}>
            {slideData.title}
          </h1>
          
          <div style={{
            background: '#fff3cd',
            padding: '25px',
            borderRadius: '12px',
            border: '3px solid #ffc107',
            marginBottom: '25px',
          }}>
            <div style={{
              fontSize: '1.3rem',
              color: '#856404',
              lineHeight: '1.6',
              textAlign: 'left',
            }}>
              <strong>重要なポイント：</strong><br/>
              • 200日移動平均線上の銘柄は成功確率が高い<br/>
              • 適切なポジションサイジングが重要<br/>
              • ストップロス設定でリスク管理<br/>
              • 過去のパターン分析に基づく判断
            </div>
          </div>
          
          <div style={{
            fontSize: '1.1rem',
            color: '#6c757d',
            fontStyle: 'italic',
          }}>
            投資判断は自己責任で行い、<br/>必ず十分な検討を行ってください
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};