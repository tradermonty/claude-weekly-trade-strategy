import {AbsoluteFill, Audio, Sequence, useCurrentFrame, useVideoConfig, interpolate, Easing, staticFile} from 'remotion';
import React from 'react';
import earningsNarration from './earnings-trade-narration-with-durations.json';

export const EarningsTradeSlides: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  const slideDurations = [
    Math.ceil((16.42 + 1) * fps), // Slide 1: ~17.4s
    Math.ceil((14.71 + 1) * fps), // Slide 2: ~15.7s  
    Math.ceil((19.56 + 1) * fps), // Slide 3: ~20.6s
    Math.ceil((16.06 + 1) * fps), // Slide 4: ~17.1s
    Math.ceil((16.82 + 1) * fps), // Slide 5: ~17.8s
    Math.ceil((22.68 + 1) * fps), // Slide 6: ~23.7s
  ];
  
  let currentSlide = 0;
  let accumulatedFrames = 0;
  
  for (let i = 0; i < slideDurations.length; i++) {
    if (frame >= accumulatedFrames && frame < accumulatedFrames + slideDurations[i]) {
      currentSlide = i;
      break;
    }
    accumulatedFrames += slideDurations[i];
  }
  
  const slideFrame = frame - accumulatedFrames;
  
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
      padding: '60px',
      opacity: slideOpacity,
    }}>
      {/* Audio Components */}
      {earningsNarration.slides.map((slide, index) => {
        const audioStartFrame = index === 0 ? 0 : slideDurations.slice(0, index).reduce((a, b) => a + b, 0);
        return (
          <Audio
            key={`audio-${index}`}
            src={staticFile(`audio/earnings-slide-${slide.slide}-narration.mp3`)}
            startFrom={audioStartFrame}
            endAt={audioStartFrame + slideDurations[index]}
          />
        );
      })}

      {/* Slide Content */}
      {currentSlide === 0 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          maxWidth: '800px',
        }}>
          <h1 style={{
            fontSize: '4rem',
            fontWeight: 'bold',
            marginBottom: '30px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            lineHeight: '1.2',
          }}>
            {slideData.title}
          </h1>
          <div style={{
            fontSize: '1.8rem',
            marginBottom: '40px',
            opacity: 0.9,
            fontWeight: '300',
          }}>
            {slideData.subtitle}
          </div>
          <div style={{
            background: 'rgba(255,255,255,0.15)',
            padding: '25px',
            borderRadius: '15px',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.2)',
            fontSize: '1.2rem',
            lineHeight: '1.6',
          }}>
            9銘柄の詳細分析とバックテストスコアによる投資判断
          </div>
        </div>
      )}

      {currentSlide === 1 && (
        <div style={{
          background: 'white',
          borderRadius: '20px',
          padding: '50px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '900px',
          width: '100%',
        }}>
          <h1 style={{
            fontSize: '3rem',
            color: '#2c3e50',
            marginBottom: '40px',
            textAlign: 'center',
            fontWeight: 'bold',
          }}>
            {slideData.title}
          </h1>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '30px',
            marginTop: '30px',
          }}>
            {[
              { label: '分析銘柄数', value: slideData.data.analyzed, color: '#3498db' },
              { label: 'Aグレード', value: slideData.data.a_grade, color: '#27ae60' },
              { label: 'Bグレード', value: slideData.data.b_grade, color: '#3498db' },
              { label: '平均EPS予想超過', value: slideData.data.avg_eps_surprise, color: '#f39c12' },
            ].map((item, index) => (
              <div key={index} style={{
                background: '#f8f9fa',
                padding: '25px',
                borderRadius: '15px',
                textAlign: 'center',
                border: `3px solid ${item.color}`,
              }}>
                <div style={{
                  fontSize: '3rem',
                  fontWeight: 'bold',
                  color: item.color,
                  marginBottom: '10px',
                }}>
                  {item.value}
                </div>
                <div style={{
                  fontSize: '1.2rem',
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
          padding: '50px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '900px',
          width: '100%',
          color: 'white',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '30px',
          }}>
            <h1 style={{
              fontSize: '3rem',
              fontWeight: 'bold',
              margin: 0,
            }}>
              {slideData.data.symbol}
            </h1>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '15px 25px',
              borderRadius: '50px',
              fontSize: '1.5rem',
              fontWeight: 'bold',
            }}>
              A-Grade ★★★★★
            </div>
          </div>
          
          <div style={{
            fontSize: '1.5rem',
            marginBottom: '40px',
            opacity: 0.9,
          }}>
            {slideData.data.name}
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '20px',
            marginBottom: '30px',
          }}>
            {[
              { label: '現在株価', value: slideData.data.price },
              { label: '1日パフォーマンス', value: slideData.data.performance },
              { label: '総合スコア', value: slideData.data.score },
              { label: '成功確率', value: slideData.data.probability },
            ].map((item, index) => (
              <div key={index} style={{
                background: 'rgba(255,255,255,0.15)',
                padding: '20px',
                borderRadius: '15px',
                textAlign: 'center',
                backdropFilter: 'blur(5px)',
              }}>
                <div style={{
                  fontSize: '2rem',
                  fontWeight: 'bold',
                  marginBottom: '5px',
                }}>
                  {item.value}
                </div>
                <div style={{
                  fontSize: '1rem',
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
          padding: '50px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '900px',
          width: '100%',
          color: 'white',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '30px',
          }}>
            <h1 style={{
              fontSize: '3rem',
              fontWeight: 'bold',
              margin: 0,
            }}>
              {slideData.data.symbol}
            </h1>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '15px 25px',
              borderRadius: '50px',
              fontSize: '1.5rem',
              fontWeight: 'bold',
            }}>
              A-Grade ★★★★★
            </div>
          </div>
          
          <div style={{
            fontSize: '1.5rem',
            marginBottom: '40px',
            opacity: 0.9,
          }}>
            {slideData.data.name}
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '20px',
            marginBottom: '30px',
          }}>
            {[
              { label: '現在株価', value: slideData.data.price },
              { label: '1日パフォーマンス', value: slideData.data.performance },
              { label: 'EPS予想超過', value: slideData.data.eps_surprise },
              { label: '総合スコア', value: slideData.data.score },
            ].map((item, index) => (
              <div key={index} style={{
                background: 'rgba(255,255,255,0.15)',
                padding: '20px',
                borderRadius: '15px',
                textAlign: 'center',
                backdropFilter: 'blur(5px)',
              }}>
                <div style={{
                  fontSize: '2rem',
                  fontWeight: 'bold',
                  marginBottom: '5px',
                }}>
                  {item.value}
                </div>
                <div style={{
                  fontSize: '1rem',
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
          padding: '50px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '900px',
          width: '100%',
        }}>
          <h1 style={{
            fontSize: '3rem',
            color: '#2c3e50',
            marginBottom: '40px',
            textAlign: 'center',
            fontWeight: 'bold',
          }}>
            {slideData.title}
          </h1>
          
          <div style={{
            display: 'grid',
            gap: '20px',
          }}>
            {[
              { symbol: 'BRZE', name: 'Braze Inc', performance: '+18.66%', highlight: '403% EPS超過' },
              { symbol: 'GWRE', name: 'Guidewire Software', performance: '+13.89%', highlight: 'ARR $1B突破' },
              { symbol: 'IOT', name: 'Samsara Inc', performance: '+12.42%', highlight: 'AI需要拡大' },
            ].map((stock, index) => (
              <div key={index} style={{
                background: 'linear-gradient(135deg, #3498db, #5dade2)',
                padding: '25px',
                borderRadius: '15px',
                color: 'white',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stock.symbol}</div>
                  <div style={{ fontSize: '1.2rem', opacity: 0.9 }}>{stock.name}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stock.performance}</div>
                  <div style={{ fontSize: '1rem', opacity: 0.8 }}>{stock.highlight}</div>
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
          padding: '50px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
          maxWidth: '900px',
          width: '100%',
          textAlign: 'center',
        }}>
          <h1 style={{
            fontSize: '3rem',
            color: '#2c3e50',
            marginBottom: '40px',
            fontWeight: 'bold',
          }}>
            {slideData.title}
          </h1>
          
          <div style={{
            background: '#fff3cd',
            padding: '30px',
            borderRadius: '15px',
            border: '3px solid #ffc107',
            marginBottom: '30px',
          }}>
            <div style={{
              fontSize: '1.5rem',
              color: '#856404',
              lineHeight: '1.8',
            }}>
              <strong>重要なポイント：</strong><br/>
              • 200日移動平均線上の銘柄は成功確率が高い<br/>
              • 適切なポジションサイジングが重要<br/>
              • ストップロス設定でリスク管理<br/>
              • 過去のパターン分析に基づく判断
            </div>
          </div>
          
          <div style={{
            fontSize: '1.2rem',
            color: '#6c757d',
            fontStyle: 'italic',
          }}>
            投資判断は自己責任で行い、必ず十分な検討を行ってください
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};