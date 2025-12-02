import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import React from 'react';

export const EarningsTradeEnglishSept5: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  const slideDurations = [
    Math.ceil(4 * fps), // Slide 1: Title - 4 seconds
    Math.ceil(4 * fps), // Slide 2: Summary Stats - 4 seconds  
    Math.ceil(5 * fps), // Slide 3: AVGO A-Grade - 5 seconds
    Math.ceil(5 * fps), // Slide 4: ZUMZ A-Grade - 5 seconds
    Math.ceil(6 * fps), // Slide 5: Top B-Grade BRZE - 6 seconds
    Math.ceil(5 * fps), // Slide 6: Other B-Grades - 5 seconds
    Math.ceil(4 * fps), // Slide 7: Key Metrics - 4 seconds
    Math.ceil(3 * fps), // Slide 8: Disclaimer/Footer - 3 seconds
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

  // Animation for elements within slides
  const elementScale = interpolate(
    slideFrame,
    [0, 30],
    [0.8, 1],
    {
      easing: Easing.out(Easing.back(1.7)),
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

      {/* Slide 1: Title */}
      {currentSlide === 0 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          maxWidth: '900px',
          transform: `scale(${elementScale})`,
        }}>
          <div style={{
            background: 'rgba(255,255,255,0.1)',
            padding: '20px',
            borderRadius: '15px',
            marginBottom: '40px',
            fontSize: '1.8rem',
            fontWeight: '500',
            backdropFilter: 'blur(10px)',
          }}>
            POST-EARNINGS ANALYSIS
          </div>
          <h1 style={{
            fontSize: '4.8rem',
            fontWeight: 'bold',
            marginBottom: '30px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            lineHeight: '1.1',
          }}>
            EARNINGS
          </h1>
          <h2 style={{
            fontSize: '4.2rem',
            fontWeight: 'bold',
            marginBottom: '40px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            lineHeight: '1.1',
            color: '#FFD700',
          }}>
            WINNERS
          </h2>
          <div style={{
            background: 'rgba(255,255,255,0.2)',
            padding: '25px',
            borderRadius: '20px',
            backdropFilter: 'blur(10px)',
            border: '2px solid rgba(255,255,255,0.3)',
            fontSize: '1.8rem',
            lineHeight: '1.4',
            fontWeight: '500',
          }}>
            SEPTEMBER 5, 2025
          </div>
        </div>
      )}

      {/* Slide 2: Summary Stats */}
      {currentSlide === 1 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          transform: `scale(${elementScale})`,
        }}>
          <h1 style={{
            fontSize: '3.5rem',
            fontWeight: 'bold',
            marginBottom: '60px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#FFD700',
          }}>
            ANALYSIS SUMMARY
          </h1>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '30px',
            marginBottom: '50px',
          }}>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '30px',
              borderRadius: '20px',
              backdropFilter: 'blur(10px)',
              border: '2px solid #27ae60',
            }}>
              <div style={{
                fontSize: '3.5rem',
                fontWeight: 'bold',
                color: '#27ae60',
                marginBottom: '15px',
              }}>2</div>
              <div style={{
                fontSize: '1.8rem',
                fontWeight: '600',
              }}>A-GRADE STOCKS</div>
            </div>
            
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '30px',
              borderRadius: '20px',
              backdropFilter: 'blur(10px)',
              border: '2px solid #3498db',
            }}>
              <div style={{
                fontSize: '3.5rem',
                fontWeight: 'bold',
                color: '#3498db',
                marginBottom: '15px',
              }}>4</div>
              <div style={{
                fontSize: '1.8rem',
                fontWeight: '600',
              }}>B-GRADE STOCKS</div>
            </div>
          </div>
          
          <div style={{
            background: 'rgba(255,215,0,0.2)',
            padding: '35px',
            borderRadius: '20px',
            backdropFilter: 'blur(10px)',
            border: '2px solid #FFD700',
          }}>
            <div style={{
              fontSize: '4.5rem',
              fontWeight: 'bold',
              color: '#FFD700',
              marginBottom: '15px',
            }}>
              158%
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: '600',
            }}>
              AVERAGE EPS SURPRISE
            </div>
          </div>
        </div>
      )}

      {/* Slide 3: AVGO A-Grade */}
      {currentSlide === 2 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          transform: `scale(${elementScale})`,
        }}>
          <div style={{
            background: 'linear-gradient(135deg, #27ae60, #2ecc71)',
            padding: '25px',
            borderRadius: '20px',
            marginBottom: '40px',
            boxShadow: '0 10px 30px rgba(39,174,96,0.3)',
          }}>
            <div style={{
              fontSize: '2.2rem',
              fontWeight: 'bold',
              marginBottom: '10px',
            }}>
              ★★★★★ A-GRADE
            </div>
            <div style={{
              fontSize: '1.5rem',
              opacity: 0.9,
            }}>
              SCORE: 87.3 | SUCCESS: 72%
            </div>
          </div>
          
          <h1 style={{
            fontSize: '7rem',
            fontWeight: 'bold',
            marginBottom: '30px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#27ae60',
          }}>
            AVGO
          </h1>
          
          <h2 style={{
            fontSize: '2.5rem',
            fontWeight: 'bold',
            marginBottom: '20px',
            opacity: 0.9,
          }}>
            BROADCOM INC
          </h2>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '25px',
            marginTop: '40px',
          }}>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '25px',
              borderRadius: '15px',
              backdropFilter: 'blur(10px)',
            }}>
              <div style={{ fontSize: '3rem', fontWeight: 'bold', color: '#FFD700' }}>+10.88%</div>
              <div style={{ fontSize: '1.4rem', marginTop: '5px' }}>1D PERFORMANCE</div>
            </div>
            
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '25px',
              borderRadius: '15px',
              backdropFilter: 'blur(10px)',
            }}>
              <div style={{ fontSize: '3rem', fontWeight: 'bold', color: '#FFD700' }}>$339.76</div>
              <div style={{ fontSize: '1.4rem', marginTop: '5px' }}>CURRENT PRICE</div>
            </div>
          </div>
        </div>
      )}

      {/* Slide 4: ZUMZ A-Grade */}
      {currentSlide === 3 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          transform: `scale(${elementScale})`,
        }}>
          <div style={{
            background: 'linear-gradient(135deg, #27ae60, #2ecc71)',
            padding: '25px',
            borderRadius: '20px',
            marginBottom: '40px',
            boxShadow: '0 10px 30px rgba(39,174,96,0.3)',
          }}>
            <div style={{
              fontSize: '2.2rem',
              fontWeight: 'bold',
              marginBottom: '10px',
            }}>
              ★★★★★ A-GRADE
            </div>
            <div style={{
              fontSize: '1.5rem',
              opacity: 0.9,
            }}>
              SCORE: 86.1 | SUCCESS: 71%
            </div>
          </div>
          
          <h1 style={{
            fontSize: '7rem',
            fontWeight: 'bold',
            marginBottom: '30px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#27ae60',
          }}>
            ZUMZ
          </h1>
          
          <h2 style={{
            fontSize: '2.5rem',
            fontWeight: 'bold',
            marginBottom: '20px',
            opacity: 0.9,
          }}>
            ZUMIEZ INC
          </h2>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '25px',
            marginTop: '40px',
          }}>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '25px',
              borderRadius: '15px',
              backdropFilter: 'blur(10px)',
            }}>
              <div style={{ fontSize: '3rem', fontWeight: 'bold', color: '#FFD700' }}>+13.77%</div>
              <div style={{ fontSize: '1.4rem', marginTop: '5px' }}>1D PERFORMANCE</div>
            </div>
            
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '25px',
              borderRadius: '15px',
              backdropFilter: 'blur(10px)',
            }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#e74c3c' }}>43.24%</div>
              <div style={{ fontSize: '1.4rem', marginTop: '5px' }}>EPS SURPRISE</div>
            </div>
          </div>
        </div>
      )}

      {/* Slide 5: Top B-Grade BRZE */}
      {currentSlide === 4 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          transform: `scale(${elementScale})`,
        }}>
          <div style={{
            background: 'linear-gradient(135deg, #3498db, #5dade2)',
            padding: '25px',
            borderRadius: '20px',
            marginBottom: '40px',
            boxShadow: '0 10px 30px rgba(52,152,219,0.3)',
          }}>
            <div style={{
              fontSize: '2.2rem',
              fontWeight: 'bold',
              marginBottom: '10px',
            }}>
              ★★★★ B-GRADE LEADER
            </div>
            <div style={{
              fontSize: '1.5rem',
              opacity: 0.9,
            }}>
              SCORE: 73.8 | SUCCESS: 62%
            </div>
          </div>
          
          <h1 style={{
            fontSize: '7rem',
            fontWeight: 'bold',
            marginBottom: '30px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#3498db',
          }}>
            BRZE
          </h1>
          
          <h2 style={{
            fontSize: '2.2rem',
            fontWeight: 'bold',
            marginBottom: '30px',
            opacity: 0.9,
          }}>
            BRAZE INC
          </h2>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '25px',
          }}>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '25px',
              borderRadius: '15px',
              backdropFilter: 'blur(10px)',
            }}>
              <div style={{ fontSize: '3rem', fontWeight: 'bold', color: '#FFD700' }}>+18.66%</div>
              <div style={{ fontSize: '1.4rem', marginTop: '5px' }}>1D PERFORMANCE</div>
            </div>
            
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '25px',
              borderRadius: '15px',
              backdropFilter: 'blur(10px)',
            }}>
              <div style={{ fontSize: '2.3rem', fontWeight: 'bold', color: '#e74c3c' }}>403.36%</div>
              <div style={{ fontSize: '1.4rem', marginTop: '5px' }}>EPS SURPRISE</div>
            </div>
          </div>
          
          <div style={{
            background: 'rgba(52,152,219,0.2)',
            padding: '20px',
            borderRadius: '15px',
            marginTop: '30px',
            border: '2px solid #3498db',
          }}>
            <div style={{ fontSize: '1.4rem', fontWeight: '500' }}>
              MASSIVE EPS BEAT DRIVEN BY AI INTEGRATION
            </div>
          </div>
        </div>
      )}

      {/* Slide 6: Other B-Grades */}
      {currentSlide === 5 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          transform: `scale(${elementScale})`,
        }}>
          <h1 style={{
            fontSize: '3.8rem',
            fontWeight: 'bold',
            marginBottom: '50px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#3498db',
          }}>
            OTHER B-GRADE STARS
          </h1>
          
          <div style={{
            display: 'grid',
            gap: '25px',
          }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '25px',
            }}>
              <div style={{
                background: 'linear-gradient(135deg, #9b59b6, #8e44ad)',
                padding: '30px',
                borderRadius: '20px',
                boxShadow: '0 8px 25px rgba(155,89,182,0.3)',
              }}>
                <div style={{ fontSize: '3.5rem', fontWeight: 'bold', marginBottom: '10px' }}>GWRE</div>
                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#FFD700', marginBottom: '5px' }}>+13.89%</div>
                <div style={{ fontSize: '1.3rem', opacity: 0.9 }}>GUIDEWIRE</div>
              </div>
              
              <div style={{
                background: 'linear-gradient(135deg, #f39c12, #e67e22)',
                padding: '30px',
                borderRadius: '20px',
                boxShadow: '0 8px 25px rgba(243,156,18,0.3)',
              }}>
                <div style={{ fontSize: '3.5rem', fontWeight: 'bold', marginBottom: '10px' }}>IOT</div>
                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#FFD700', marginBottom: '5px' }}>+12.42%</div>
                <div style={{ fontSize: '1.3rem', opacity: 0.9 }}>SAMSARA</div>
              </div>
            </div>
            
            <div style={{
              background: 'rgba(255,255,255,0.15)',
              padding: '25px',
              borderRadius: '15px',
              backdropFilter: 'blur(10px)',
            }}>
              <div style={{ fontSize: '2.2rem', fontWeight: 'bold', marginBottom: '10px', color: '#16a085' }}>DOCU +7.00%</div>
              <div style={{ fontSize: '1.4rem', opacity: 0.9 }}>DOCUSIGN - RAISED FY2026 GUIDANCE</div>
            </div>
          </div>
        </div>
      )}

      {/* Slide 7: Key Metrics */}
      {currentSlide === 6 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          transform: `scale(${elementScale})`,
        }}>
          <h1 style={{
            fontSize: '3.5rem',
            fontWeight: 'bold',
            marginBottom: '60px',
            textShadow: '0 4px 8px rgba(0,0,0,0.3)',
            color: '#FFD700',
          }}>
            KEY INSIGHTS
          </h1>
          
          <div style={{
            display: 'grid',
            gap: '30px',
          }}>
            <div style={{
              background: 'rgba(255,255,255,0.2)',
              padding: '30px',
              borderRadius: '20px',
              backdropFilter: 'blur(10px)',
              border: '2px solid #27ae60',
            }}>
              <div style={{
                fontSize: '2.5rem',
                fontWeight: 'bold',
                color: '#27ae60',
                marginBottom: '15px',
              }}>AI THEME DOMINATES</div>
              <div style={{
                fontSize: '1.6rem',
                lineHeight: '1.4',
              }}>
                AVGO, BRZE driving growth with AI integration
              </div>
            </div>
            
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '25px',
            }}>
              <div style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '25px',
                borderRadius: '15px',
                backdropFilter: 'blur(10px)',
                border: '2px solid #3498db',
              }}>
                <div style={{ fontSize: '2.8rem', fontWeight: 'bold', color: '#3498db', marginBottom: '10px' }}>67%</div>
                <div style={{ fontSize: '1.4rem' }}>AVG SUCCESS RATE</div>
                <div style={{ fontSize: '1.1rem', opacity: 0.8, marginTop: '5px' }}>A & B GRADES</div>
              </div>
              
              <div style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '25px',
                borderRadius: '15px',
                backdropFilter: 'blur(10px)',
                border: '2px solid #e74c3c',
              }}>
                <div style={{ fontSize: '2.8rem', fontWeight: 'bold', color: '#e74c3c', marginBottom: '10px' }}>13.2%</div>
                <div style={{ fontSize: '1.4rem' }}>AVG GAP SIZE</div>
                <div style={{ fontSize: '1.1rem', opacity: 0.8, marginTop: '5px' }}>TOP 6 STOCKS</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Slide 8: Disclaimer/Footer */}
      {currentSlide === 7 && (
        <div style={{
          textAlign: 'center',
          color: 'white',
          transform: `scale(${elementScale})`,
          maxWidth: '900px',
        }}>
          <div style={{
            background: 'rgba(255,193,7,0.2)',
            padding: '30px',
            borderRadius: '20px',
            backdropFilter: 'blur(10px)',
            border: '2px solid #FFC107',
            marginBottom: '30px',
          }}>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              color: '#FFC107',
              marginBottom: '20px',
            }}>
              ⚠️ RISK DISCLAIMER
            </div>
            <div style={{
              fontSize: '1.4rem',
              lineHeight: '1.5',
              opacity: 0.9,
            }}>
              Educational analysis only. Past performance doesn't guarantee future results. 
              Always use proper risk management and position sizing.
            </div>
          </div>
          
          <div style={{
            background: 'rgba(255,255,255,0.1)',
            padding: '25px',
            borderRadius: '15px',
            backdropFilter: 'blur(10px)',
          }}>
            <div style={{ fontSize: '1.6rem', fontWeight: '600', marginBottom: '10px' }}>
              FOLLOW FOR DAILY ANALYSIS
            </div>
            <div style={{ fontSize: '1.2rem', opacity: 0.8 }}>
              Generated: September 5, 2025 | 20-Year Backtest System
            </div>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};