import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import React from 'react';

export const EarningsTradeEnglish: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  const slideDurations = [
    Math.ceil(4 * fps), // Slide 1: 4 seconds
    Math.ceil(4 * fps), // Slide 2: 4 seconds
    Math.ceil(4 * fps), // Slide 3: 4 seconds
    Math.ceil(4 * fps), // Slide 4: 4 seconds
    Math.ceil(4 * fps), // Slide 5: 4 seconds
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

  return (
    <AbsoluteFill style={{
      background: backgroundGradient,
      fontFamily: "'SF Pro Display', 'Helvetica Neue', Arial, sans-serif",
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '40px',
      opacity: slideOpacity,
    }}>

      {/* Slide Content */}
      {currentSlide === 0 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          maxWidth: '900px',
        }}>
          <h1 style={{
            fontSize: '4.5rem',
            fontWeight: 'bold',
            marginBottom: '40px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            lineHeight: '1.1',
          }}>
            EARNINGS
          </h1>
          <h2 style={{
            fontSize: '3.5rem',
            fontWeight: 'bold',
            marginBottom: '50px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            lineHeight: '1.1',
            color: '#FFD700',
          }}>
            WINNERS
          </h2>
          <div style={{
            background: 'rgba(255,255,255,0.2)',
            padding: '30px',
            borderRadius: '20px',
            backdropFilter: 'blur(10px)',
            border: '2px solid rgba(255,255,255,0.3)',
            fontSize: '2rem',
            lineHeight: '1.4',
            fontWeight: '500',
          }}>
            9 STOCKS ANALYZED
          </div>
        </div>
      )}

      {currentSlide === 1 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
        }}>
          <h1 style={{
            fontSize: '5rem',
            fontWeight: 'bold',
            marginBottom: '60px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#27ae60',
          }}>
            2 A-GRADE
          </h1>
          <h2 style={{
            fontSize: '4rem',
            fontWeight: 'bold',
            marginBottom: '60px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#3498db',
          }}>
            4 B-GRADE
          </h2>
          <div style={{
            background: 'rgba(255,255,255,0.2)',
            padding: '40px',
            borderRadius: '20px',
            backdropFilter: 'blur(10px)',
            border: '2px solid rgba(255,255,255,0.3)',
          }}>
            <div style={{
              fontSize: '4rem',
              fontWeight: 'bold',
              color: '#FFD700',
              marginBottom: '20px',
            }}>
              158%
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: '500',
            }}>
              AVG EPS BEAT
            </div>
          </div>
        </div>
      )}

      {currentSlide === 2 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
        }}>
          <div style={{
            background: 'rgba(255,255,255,0.2)',
            padding: '30px',
            borderRadius: '20px',
            backdropFilter: 'blur(10px)',
            border: '2px solid #FFD700',
            marginBottom: '60px',
          }}>
            <div style={{
              fontSize: '2.5rem',
              fontWeight: 'bold',
              color: '#FFD700',
              marginBottom: '10px',
            }}>
              ★★★★★ A-GRADE
            </div>
          </div>
          
          <h1 style={{
            fontSize: '6rem',
            fontWeight: 'bold',
            marginBottom: '40px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#27ae60',
          }}>
            AVGO
          </h1>
          
          <h2 style={{
            fontSize: '4rem',
            fontWeight: 'bold',
            marginBottom: '60px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#FFD700',
          }}>
            +10.88%
          </h2>
          
          <div style={{
            fontSize: '2.2rem',
            fontWeight: '500',
            opacity: 0.9,
          }}>
            BROADCOM
          </div>
        </div>
      )}

      {currentSlide === 3 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
        }}>
          <div style={{
            background: 'rgba(255,255,255,0.2)',
            padding: '30px',
            borderRadius: '20px',
            backdropFilter: 'blur(10px)',
            border: '2px solid #FFD700',
            marginBottom: '60px',
          }}>
            <div style={{
              fontSize: '2.5rem',
              fontWeight: 'bold',
              color: '#FFD700',
              marginBottom: '10px',
            }}>
              ★★★★★ A-GRADE
            </div>
          </div>
          
          <h1 style={{
            fontSize: '6rem',
            fontWeight: 'bold',
            marginBottom: '40px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#27ae60',
          }}>
            ZUMZ
          </h1>
          
          <h2 style={{
            fontSize: '4rem',
            fontWeight: 'bold',
            marginBottom: '60px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#FFD700',
          }}>
            +13.77%
          </h2>
          
          <div style={{
            fontSize: '2.2rem',
            fontWeight: '500',
            opacity: 0.9,
          }}>
            ZUMIEZ
          </div>
        </div>
      )}

      {currentSlide === 4 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
        }}>
          <h1 style={{
            fontSize: '4rem',
            fontWeight: 'bold',
            marginBottom: '80px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#3498db',
          }}>
            B-GRADE STARS
          </h1>
          
          <div style={{
            display: 'grid',
            gap: '40px',
          }}>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '30px',
              borderRadius: '20px',
              backdropFilter: 'blur(10px)',
              border: '2px solid #e74c3c',
            }}>
              <div style={{ fontSize: '3rem', fontWeight: 'bold', marginBottom: '10px', color: '#e74c3c' }}>BRZE</div>
              <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#FFD700' }}>+18.66%</div>
            </div>
            
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '20px',
            }}>
              <div style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '25px',
                borderRadius: '20px',
                backdropFilter: 'blur(10px)',
                border: '2px solid #9b59b6',
              }}>
                <div style={{ fontSize: '2.2rem', fontWeight: 'bold', marginBottom: '10px', color: '#9b59b6' }}>GWRE</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#FFD700' }}>+13.89%</div>
              </div>
              
              <div style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '25px',
                borderRadius: '20px',
                backdropFilter: 'blur(10px)',
                border: '2px solid #f39c12',
              }}>
                <div style={{ fontSize: '2.2rem', fontWeight: 'bold', marginBottom: '10px', color: '#f39c12' }}>IOT</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#FFD700' }}>+12.42%</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};