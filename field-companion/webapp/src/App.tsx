import { useState, useEffect } from 'react';
import {
  getMobileAppInfo,
  getMobileAppDownloadUrl,
  checkBackendHealth,
  API_BASE,
} from './services/api';
import type { MobileAppInfo } from './services/api';
import './App.css';

type PreviewTab = 'listen' | 'photo' | 'journal' | 'model';

export default function App() {
  const [appInfo, setAppInfo] = useState<MobileAppInfo | null>(null);
  const [downloadInitiated, setDownloadInitiated] = useState(false);
  const [backendStatus, setBackendStatus] = useState<{ online: boolean; speciesCount?: number }>({
    online: false,
    speciesCount: 731,
  });
  const [activePreviewTab, setActivePreviewTab] = useState<PreviewTab>('listen');
  const [showExpoInstructions, setShowExpoInstructions] = useState(false);

  useEffect(() => {
    let mounted = true;

    // Load download info and backend health
    getMobileAppInfo().then((info) => {
      if (mounted) setAppInfo(info);
    });

    checkBackendHealth().then((status) => {
      if (mounted) setBackendStatus(status);
    });

    return () => {
      mounted = false;
    };
  }, []);

  const handleDownloadClick = () => {
    setDownloadInitiated(true);
    const downloadUrl = getMobileAppDownloadUrl();
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', 'FieldCompanion.apk');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
      setDownloadInitiated(false);
    }, 5000);
  };

  return (
    <div className="landing-container">
      {/* Navigation Header */}
      <header className="navbar">
        <div className="nav-inner">
          <div className="brand">
            <span className="brand-logo">🌱</span>
            <div className="brand-text">
              <span className="brand-name">Field Companion</span>
              <span className="brand-tag">Mobile Nature Guide</span>
            </div>
          </div>

          <div className="nav-badges">
            <div className="offline-pill" title="Works without internet connection">
              <span className="status-dot status-online" />
              <span>100% Offline Capable</span>
            </div>
            <a
              href="#download"
              className="btn-primary btn-nav-download"
              id="nav-download-btn"
            >
              <span>Download APK</span>
            </a>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-tag">
            <span>📱 STANDALONE MOBILE APP</span>
            <span className="tag-separator">•</span>
            <span>NO CELL TOWERS REQUIRED</span>
          </div>

          <h1 className="hero-title">
            Your Voice-First Nature Companion in the Wild.
          </h1>

          <p className="hero-subtitle">
            Identify birds by their calls, recognize plants with your camera, and keep a field diary deep in the forest. Engineered to run 100% on your device with local Gemma intelligence and BirdNET bioacoustics.
          </p>

          {/* Download Action Area */}
          <div className="hero-cta-group" id="download">
            <button
              className="btn-primary btn-download-hero"
              onClick={handleDownloadClick}
              id="hero-download-apk-btn"
            >
              <svg className="icon download-icon" viewBox="0 0 24 24">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              <div className="btn-download-text">
                <span className="btn-main-label">
                  {downloadInitiated ? 'Downloading APK...' : 'Download Android APK'}
                </span>
                <span className="btn-sub-label">
                  v1.0.0 • {appInfo?.file_size_formatted || '52.4 MB'} • Direct from Server
                </span>
              </div>
            </button>

            <button
              className="btn-secondary btn-expo-hero"
              onClick={() => setShowExpoInstructions(!showExpoInstructions)}
              id="hero-expo-btn"
            >
              <svg className="icon" viewBox="0 0 24 24">
                <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
                <line x1="12" y1="18" x2="12.01" y2="18" />
              </svg>
              <span>{showExpoInstructions ? 'Hide Expo Go' : 'Try in Expo Go (iOS/Android)'}</span>
            </button>
          </div>

          {downloadInitiated && (
            <div className="download-toast">
              ✓ <strong>FieldCompanion.apk download started!</strong> Check your browser notification or files folder to install.
            </div>
          )}

          {/* Server Connection Indicator */}
          <div className="server-status-strip">
            <span
              className={`status-dot ${backendStatus.online ? 'status-online' : 'status-offline'}`}
            />
            <span className="server-status-text">
              Backend Model Server: <code>{API_BASE}</code> •{' '}
              {backendStatus.online
                ? `Online (${backendStatus.speciesCount} species loaded)`
                : 'Local / Offline Standalone Mode'}
            </span>
          </div>

          {/* Expo Go Quick Instructions Dropdown */}
          {showExpoInstructions && (
            <div className="expo-panel">
              <div className="expo-header">
                <h3>📲 Instant Testing with Expo Go (No APK Installation)</h3>
                <button
                  className="btn-close-sm"
                  onClick={() => setShowExpoInstructions(false)}
                >
                  ✕
                </button>
              </div>
              <p className="expo-desc">
                If you are on an iPhone or prefer not to sideload an APK file, you can run Field Companion directly inside the free Expo Go app:
              </p>
              <div className="expo-steps-grid">
                <div className="expo-step">
                  <span className="step-num">1</span>
                  <span>Install <strong>Expo Go</strong> from the App Store or Google Play</span>
                </div>
                <div className="expo-step">
                  <span className="step-num">2</span>
                  <span>
                    In terminal, run: <br />
                    <code>cd field-companion/mobile && npx expo start --go</code>
                  </span>
                </div>
                <div className="expo-step">
                  <span className="step-num">3</span>
                  <span>Scan the terminal QR code with your phone camera</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Interactive Phone Mockup */}
        <div className="hero-device-wrapper">
          <div className="phone-device">
            <div className="phone-notch">
              <div className="notch-camera" />
              <div className="notch-speaker" />
            </div>

            <div className="phone-screen">
              {/* Phone Status Bar */}
              <div className="phone-status-bar">
                <span>9:41</span>
                <div className="phone-status-icons">
                  <span className="offline-mode-chip">🌲 Offline Mode</span>
                  <span>🔋 98%</span>
                </div>
              </div>

              {/* Phone App Content based on selected tab */}
              <div className="phone-app-body">
                {activePreviewTab === 'listen' && (
                  <div className="phone-screen-view">
                    <div className="preview-app-header">
                      <span className="preview-app-title">Field Companion</span>
                      <span className="preview-status-pill">● Audio Active</span>
                    </div>

                    <div className="preview-listen-box">
                      <div className="pulsing-audio-ring">
                        <div className="ring-pulse" />
                        <svg className="preview-mic-icon" viewBox="0 0 24 24">
                          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                          <line x1="12" y1="19" x2="12" y2="23" />
                        </svg>
                      </div>
                      <span className="preview-listen-text">Listening for bird calls...</span>
                    </div>

                    <div className="preview-result-card">
                      <div className="result-species-row">
                        <div>
                          <strong className="result-name">Oriental Magpie-Robin</strong>
                          <p className="result-sci">Copsychus saularis</p>
                        </div>
                        <span className="confidence-badge">94% match</span>
                      </div>
                      <div className="result-lookfor">
                        <p className="lookfor-label">What to look for:</p>
                        <p className="lookfor-text">
                          Bold black and white plumage with white wing patch and cocked tail.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {activePreviewTab === 'photo' && (
                  <div className="phone-screen-view">
                    <div className="preview-app-header">
                      <span className="preview-app-title">Camera Lens</span>
                      <span className="preview-status-pill">● Gemma Vision</span>
                    </div>

                    <div className="preview-camera-lens">
                      <div className="lens-crosshair">
                        <div className="lens-corner tl" />
                        <div className="lens-corner tr" />
                        <div className="lens-corner bl" />
                        <div className="lens-corner br" />
                        <span className="lens-detect-label">Neem Tree (Azadirachta indica)</span>
                      </div>
                    </div>

                    <div className="preview-result-card">
                      <div className="result-species-row">
                        <div>
                          <strong className="result-name">Neem Tree</strong>
                          <p className="result-sci">Azadirachta indica</p>
                        </div>
                        <span className="confidence-badge">98% match</span>
                      </div>
                      <p className="safety-footnote">
                        ⚠️ Do not ingest or consume any wild plant based on automated identification.
                      </p>
                    </div>
                  </div>
                )}

                {activePreviewTab === 'journal' && (
                  <div className="phone-screen-view">
                    <div className="preview-app-header">
                      <span className="preview-app-title">Field Journal</span>
                      <span className="preview-status-pill">● Local SQLite</span>
                    </div>

                    <div className="preview-journal-list">
                      <div className="journal-card">
                        <div className="journal-header-row">
                          <strong>Oriental Magpie-Robin</strong>
                          <span className="journal-time">Today, 08:14</span>
                        </div>
                        <p className="journal-coords mono">28.6139° N, 77.2090° E</p>
                        <p className="journal-note">Singing loudly from the eucalyptus canopy.</p>
                      </div>

                      <div className="journal-card">
                        <div className="journal-header-row">
                          <strong>Common Myna</strong>
                          <span className="journal-time">Yesterday, 17:30</span>
                        </div>
                        <p className="journal-coords mono">28.6142° N, 77.2088° E</p>
                        <p className="journal-note">Foraging in lawn grass in pairs.</p>
                      </div>
                    </div>
                  </div>
                )}

                {activePreviewTab === 'model' && (
                  <div className="phone-screen-view">
                    <div className="preview-app-header">
                      <span className="preview-app-title">Model Pack</span>
                      <span className="preview-status-pill">● Active</span>
                    </div>

                    <div className="preview-pack-card">
                      <div className="pack-title-row">
                        <span className="pack-icon">🧠</span>
                        <div>
                          <strong>Google Gemma 4 E2B</strong>
                          <p className="pack-sub">On-Device Multimodal Neural Network</p>
                        </div>
                      </div>
                      <div className="pack-specs">
                        <div className="spec-item">
                          <span>Size</span>
                          <strong className="mono">1.8 GB</strong>
                        </div>
                        <div className="spec-item">
                          <span>Status</span>
                          <strong className="text-moss">Pre-installed</strong>
                        </div>
                        <div className="spec-item">
                          <span>Cloud calls</span>
                          <strong className="mono">0</strong>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Phone Interactive Tabs */}
              <div className="phone-preview-switcher">
                <button
                  className={`phone-tab ${activePreviewTab === 'listen' ? 'active' : ''}`}
                  onClick={() => setActivePreviewTab('listen')}
                >
                  🎙️ Listen
                </button>
                <button
                  className={`phone-tab ${activePreviewTab === 'photo' ? 'active' : ''}`}
                  onClick={() => setActivePreviewTab('photo')}
                >
                  📷 Photo
                </button>
                <button
                  className={`phone-tab ${activePreviewTab === 'journal' ? 'active' : ''}`}
                  onClick={() => setActivePreviewTab('journal')}
                >
                  📖 Diary
                </button>
                <button
                  className={`phone-tab ${activePreviewTab === 'model' ? 'active' : ''}`}
                  onClick={() => setActivePreviewTab('model')}
                >
                  🧠 Model
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section className="features-section">
        <div className="section-header">
          <span className="meta-text">ENGINEERED FOR THE TRAIL</span>
          <h2>Zero Signal. 100% On-Device Intelligence.</h2>
          <p className="section-sub">
            Designed specifically for hikers, naturalists, and birdwatchers venturing beyond cellular coverage.
          </p>
        </div>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon-box">🎙️</div>
            <h3>BirdNET Bioacoustics</h3>
            <p>
              Records songs and chirps with high-fidelity acoustic processing. Automatically filters ambient wind noise and isolates candidate bird species against regional checklists.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-box">👁️</div>
            <h3>Multimodal Visual Recognition</h3>
            <p>
              Captures photos with your phone camera, instantly downscaling to optimal model resolution and reasoning over diagnostic field marks: tail plumage, beak geometry, and leaf serrations.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-box">🌲</div>
            <h3>Offline Checklist Grounding</h3>
            <p>
              Pre-seeded with 731 verified birds, mammals, and trees in SQLite. The model verifies every suggestion against real regional occurrence data to prevent hallucinations.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-box">📖</div>
            <h3>Local Field Journal & GPS</h3>
            <p>
              Logs your outdoor observations with timestamp, GPS coordinates, and personal field notes. Stored exclusively in local phone storage with zero analytics or telemetry.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-box">🗣️</div>
            <h3>Voice Queries & Spoken Advice</h3>
            <p>
              Ask spoken questions like "What bird has a white wing stripe?" and receive concise, natural spoken guidance kept strictly under 25 words so you don't break your field concentration.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-box">🔋</div>
            <h3>Minimal Battery Overhead</h3>
            <p>
              Lightweight quantized execution ensures you can spend 3 to 4 hours actively exploring on trails without draining your phone's battery.
            </p>
          </div>
        </div>
      </section>

      {/* 3-Step Sideloading Instructions */}
      <section className="install-section">
        <div className="section-header">
          <span className="meta-text">EASY SETUP</span>
          <h2>How to Install on Your Android Phone</h2>
          <p className="section-sub">
            No Google Play account needed. Download and install in 3 simple steps:
          </p>
        </div>

        <div className="steps-container">
          <div className="step-card">
            <div className="step-badge">Step 1</div>
            <h3>Download APK</h3>
            <p>
              Tap the download button on this page. Your phone will download <code>FieldCompanion.apk</code> directly from this server.
            </p>
          </div>

          <div className="step-card">
            <div className="step-badge">Step 2</div>
            <h3>Allow Installation</h3>
            <p>
              Open the downloaded file. If Android displays <em>"Install unknown apps"</em>, tap <strong>Settings</strong> and toggle <strong>Allow from this source</strong>.
            </p>
          </div>

          <div className="step-card">
            <div className="step-badge">Step 3</div>
            <h3>Open & Explore</h3>
            <p>
              Tap <strong>Install</strong>. Once installed, launch Field Companion, allow camera and microphone permissions, and head outdoors!
            </p>
          </div>
        </div>

        <div className="install-cta-wrap">
          <button
            className="btn-primary"
            onClick={handleDownloadClick}
            id="install-section-download-btn"
          >
            <span>📥 Download FieldCompanion.apk (Direct)</span>
          </button>
        </div>
      </section>

      {/* Technical Specifications */}
      <section className="specs-section">
        <div className="section-header">
          <span className="meta-text">SYSTEM DETAILS</span>
          <h2>Technical Architecture</h2>
        </div>

        <div className="specs-table-wrapper">
          <table className="specs-table">
            <tbody>
              <tr>
                <td>Application Architecture</td>
                <td>React Native (Expo SDK 52) Native Mobile App</td>
              </tr>
              <tr>
                <td>Package Identifier</td>
                <td className="mono">com.fieldcompanion.app</td>
              </tr>
              <tr>
                <td>Model Runtime</td>
                <td>Google Gemma 4 E2B (On-Device Neural Weights)</td>
              </tr>
              <tr>
                <td>Bioacoustics Engine</td>
                <td>BirdNET Bioacoustics + FFT Spectral Analysis</td>
              </tr>
              <tr>
                <td>Database</td>
                <td>SQLite on-device (731 regional species pre-seeded)</td>
              </tr>
              <tr>
                <td>Telemetry / Cloud Tracking</td>
                <td><strong>Zero</strong> (Complete privacy, offline-first)</td>
              </tr>
              <tr>
                <td>Distribution Format</td>
                <td>Standalone Android APK + Expo Go development client</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <strong>Field Companion</strong>
            <p className="footer-tagline">Offline, voice-first nature companion on mobile.</p>
          </div>

          <div className="footer-disclaimer">
            <p>⚠️ <strong>Field Safety Footnote:</strong> Do not eat or touch any plant or fungus based on automated identification.</p>
          </div>

          <div className="footer-copyright">
            <p>© 2026 Field Companion • Built for the wild • Touch Grass Edition</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
