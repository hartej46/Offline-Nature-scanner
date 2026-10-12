import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';

import { colors, spacing, typography, layout } from '../styles/theme';
import { identifyAudioUri } from '../services/api';
import type { IdentifyResponse } from '../services/api';

interface ListeningScreenProps {
  onStop: () => void;
  onShowResult?: (result: IdentifyResponse) => void;
}

export default function ListeningScreen({ onStop, onShowResult }: ListeningScreenProps) {
  const [seconds, setSeconds] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Listening for bird calls and nature sounds...');

  const recordingRef = useRef<Audio.Recording | null>(null);
  const timerRef = useRef<any>(null);
  const isMountedRef = useRef(true);

  // Initialize and start real microphone recording on mount
  useEffect(() => {
    isMountedRef.current = true;
    startRecordingSession();

    return () => {
      isMountedRef.current = false;
      stopTimer();
      stopAndCleanupRecording();
    };
  }, []);

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const stopAndCleanupRecording = async () => {
    if (recordingRef.current) {
      try {
        const status = await recordingRef.current.getStatusAsync();
        if (status.isRecording) {
          await recordingRef.current.stopAndUnloadAsync();
        }
      } catch (e) {
        // Ignored during cleanup
      } finally {
        recordingRef.current = null;
      }
    }
  };

  const startRecordingSession = async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert(
          'Microphone Permission Needed',
          'Please grant microphone permission to record nature and bird sounds in the field.',
          [{ text: 'OK', onPress: onStop }]
        );
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      if (!isMountedRef.current) {
        await recording.stopAndUnloadAsync().catch(() => {});
        return;
      }

      recordingRef.current = recording;
      setIsRecording(true);

      // Start duration timer only once recording is active
      timerRef.current = setInterval(() => {
        setSeconds((prev) => {
          if (prev >= 30) {
            // Auto-stop at 30 seconds
            handleAnalyze();
            return 30;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err) {
      console.error('Failed to start recording session:', err);
      Alert.alert(
        'Recording Error',
        'Could not access microphone on this device.',
        [{ text: 'Back', onPress: onStop }]
      );
    }
  };

  const handleStopImmediately = async () => {
    stopTimer();
    setIsRecording(false);
    setAnalyzing(false);
    await stopAndCleanupRecording();
    onStop();
  };

  const handleAnalyze = async () => {
    if (analyzing) return;

    // 1. STOP TIMER IMMEDIATELY so elapsed seconds and waveform freeze
    stopTimer();

    // 2. STOP RECORDING IMMEDIATELY so microphone shuts off while thinking
    setIsRecording(false);
    setAnalyzing(true);
    setStatusMessage('Stopping microphone and saving audio file...');

    let recordedUri: string | null = null;

    try {
      if (recordingRef.current) {
        try {
          const status = await recordingRef.current.getStatusAsync();
          if (status.isRecording) {
            await recordingRef.current.stopAndUnloadAsync();
          }
          recordedUri = recordingRef.current.getURI();
        } finally {
          recordingRef.current = null;
        }
      }

      if (!recordedUri) {
        Alert.alert('No Audio', 'No audio was captured. Please record again.');
        handleStopImmediately();
        return;
      }

      if (!isMountedRef.current) return;

      // 3. AI is thinking — microphone is 100% OFF
      setStatusMessage('Analyzing audio with BirdNET & Gemma...');
      const res = await identifyAudioUri(recordedUri, 'field_recording.m4a');

      if (isMountedRef.current && onShowResult) {
        onShowResult(res);
      }
    } catch (err: any) {
      console.error('Audio identification error:', err);
      if (isMountedRef.current) {
        Alert.alert(
          'Analysis Failed',
          err?.message || 'Server was unable to process this audio recording. Please verify local server is reachable.',
          [{ text: 'OK', onPress: onStop }]
        );
      }
    } finally {
      if (isMountedRef.current) {
        setAnalyzing(false);
      }
    }
  };

  const formattedTime = `00:${seconds.toString().padStart(2, '0')}`;

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <View style={styles.center}>
          {/* Visual indicator: pulsing ring when recording, spinner when thinking */}
          {analyzing ? (
            <View style={styles.thinkingContainer}>
              <ActivityIndicator color={colors.moss} size="large" />
              <Text style={styles.thinkingBadge}>MICROPHONE STOPPED • ANALYZING</Text>
            </View>
          ) : (
            <View style={styles.pulseOuter}>
              <View style={styles.pulseInner}>
                <View style={styles.dot} />
              </View>
            </View>
          )}

          {/* Waveform: animates ONLY while isRecording is true */}
          <View style={styles.waveformContainer}>
            <View style={[styles.waveBar, { height: isRecording ? 8 + (seconds % 4) * 6 : 4 }]} />
            <View style={[styles.waveBar, { height: isRecording ? 18 + (seconds % 3) * 5 : 6 }]} />
            <View style={[styles.waveBar, { height: isRecording ? 28 - (seconds % 5) * 4 : 8 }]} />
            <View style={[styles.waveBar, { height: isRecording ? 14 + (seconds % 2) * 8 : 4 }]} />
            <View style={[styles.waveBar, { height: isRecording ? 24 + (seconds % 4) * 4 : 6 }]} />
            <View style={[styles.waveBar, { height: isRecording ? 30 - (seconds % 3) * 6 : 8 }]} />
            <View style={[styles.waveBar, { height: isRecording ? 12 + (seconds % 5) * 4 : 4 }]} />
            <View style={[styles.waveBar, { height: isRecording ? 22 - (seconds % 2) * 6 : 6 }]} />
            <View style={[styles.waveBar, { height: isRecording ? 10 + (seconds % 4) * 4 : 4 }]} />
          </View>

          <Text style={styles.timerText}>{formattedTime} / 00:30</Text>
          <Text style={styles.listeningTitle}>
            {analyzing ? 'Processing Audio...' : 'Listening for nature sounds...'}
          </Text>
          <Text style={styles.subtext}>
            {analyzing
              ? 'Microphone is stopped. Identifying acoustic signatures...'
              : 'Hold phone steadily toward the bird or sound source'}
          </Text>
        </View>

        <View style={styles.footer}>
          {analyzing ? (
            <View style={styles.loadingBox}>
              <ActivityIndicator color={colors.moss} size="small" />
              <Text style={styles.loadingText}>{statusMessage}</Text>
            </View>
          ) : (
            <>
              <TouchableOpacity
                style={[styles.analyzeBtn, !isRecording && styles.btnDisabled]}
                onPress={handleAnalyze}
                disabled={!isRecording}
                activeOpacity={0.8}
              >
                <Text style={styles.analyzeBtnText}>
                  {seconds < 2 ? 'Recording Audio...' : 'Stop & Analyze Recording'}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.stopBtn} onPress={handleStopImmediately}>
                <Text style={styles.stopBtnText}>Cancel</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.paper,
  },
  container: {
    flex: 1,
    paddingHorizontal: spacing.lg,
    justifyContent: 'space-between',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  thinkingContainer: {
    height: 140,
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  thinkingBadge: {
    fontFamily: typography.fontMono,
    fontSize: 10,
    color: colors.moss,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  pulseOuter: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.moss,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(79, 107, 58, 0.05)',
    marginBottom: spacing.lg,
  },
  pulseInner: {
    width: 90,
    height: 90,
    borderRadius: 45,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.moss,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dot: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.moss,
  },
  waveformContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    height: 36,
    marginBottom: spacing.sm,
  },
  waveBar: {
    width: 2,
    backgroundColor: colors.moss,
    borderRadius: 1,
  },
  timerText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeSm,
    color: colors.muted,
    marginBottom: spacing.xs,
  },
  listeningTitle: {
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeXl,
    color: colors.ink,
    marginTop: spacing.xs,
    textAlign: 'center',
  },
  subtext: {
    fontSize: typography.sizeSm,
    color: colors.muted,
    marginTop: spacing.xs,
    textAlign: 'center',
    maxWidth: 280,
  },
  footer: {
    paddingBottom: spacing.xl,
    alignItems: 'center',
    gap: spacing.sm,
    width: '100%',
  },
  analyzeBtn: {
    backgroundColor: colors.moss,
    paddingVertical: spacing.md,
    borderRadius: layout.borderRadius,
    width: '100%',
    alignItems: 'center',
    minHeight: layout.tapTarget,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  analyzeBtnText: {
    color: colors.paper,
    fontFamily: typography.fontSans,
    fontSize: typography.sizeBase,
    fontWeight: '600',
  },
  stopBtn: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    minHeight: layout.tapTarget,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopBtnText: {
    color: colors.muted,
    fontSize: typography.sizeSm,
  },
  loadingBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.md,
  },
  loadingText: {
    fontSize: typography.sizeSm,
    color: colors.muted,
    fontStyle: 'italic',
  },
});
