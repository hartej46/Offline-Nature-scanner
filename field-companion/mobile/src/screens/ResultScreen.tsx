import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing, typography, layout } from '../styles/theme';
import { addJournalEntry, getApiBaseUrl } from '../services/api';
import type { IdentifyResponse } from '../services/api';

// ExponentAV native module is not bundled in Expo Go SDK 57
const AudioModule: any = null;


interface ResultScreenProps {
  result: IdentifyResponse;
  onBack: () => void;
  onSaveToJournal: () => void;
}

export default function ResultScreen({
  result,
  onBack,
  onSaveToJournal,
}: ResultScreenProps) {
  const [saved, setSaved] = useState(false);
  const [userNote, setUserNote] = useState('');
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [isPlayingTts, setIsPlayingTts] = useState(false);
  const soundRef = useRef<any>(null);

  useEffect(() => {
    return () => {
      if (soundRef.current) {
        soundRef.current.unloadAsync().catch(() => {});
      }
    };
  }, []);

  let primarySpecies = '';
  let sciName = '';
  let confidenceScore = 0.85;
  let candidates: Array<{ name: string; sci: string }> = [];

  // Parse tool results
  const toolResults = result.tool_results || [];
  for (const tr of toolResults) {
    if (tr.result && typeof tr.result === 'object') {
      const res = tr.result as any;
      if (res.common_name) {
        primarySpecies = res.common_name;
        sciName = res.sci_name || '';
      }
      if (res.candidates && Array.isArray(res.candidates)) {
        candidates = res.candidates.map((c: any) => ({
          name: c.common_name || '',
          sci: c.sci_name || '',
        }));
      }
    }
  }

  // Parse birdnet detections
  if (!primarySpecies && result.birdnet_detections && result.birdnet_detections.length > 0) {
    const top = result.birdnet_detections[0];
    primarySpecies = top.common_name;
    sciName = top.sci_name;
    confidenceScore = top.confidence;
    candidates = result.birdnet_detections.slice(1).map((d) => ({
      name: d.common_name,
      sci: d.sci_name,
    }));
  }

  if (!primarySpecies) {
    const lines = result.response.split('\n').filter((l) => l.trim().length > 0);
    primarySpecies = lines[0] || 'Observation';
  }

  const confidenceLevel =
    confidenceScore >= 0.7 ? 'high' : confidenceScore >= 0.4 ? 'mid' : 'low';
  const confidencePercent = Math.round(confidenceScore * 100);

  const handleSave = async () => {
    setSaved(true);
    try {
      await addJournalEntry({
        common_name: primarySpecies,
        sci_name: sciName,
        confidence: confidenceScore,
        source: result.mode === 'bird_audio' ? 'audio' : (result.mode === 'voice_query' ? 'voice' : 'text'),
        response: result.response,
        notes: userNote,
        audio_path: result.audio_path,
        image_path: result.image_path,
      });
    } catch (err) {
      console.warn('Failed to save to journal:', err);
    }
    setTimeout(() => {
      onSaveToJournal();
    }, 600);
  };

  const handlePlayTts = async () => {
    try {
      if (soundRef.current) {
        await soundRef.current.stopAsync();
        await soundRef.current.unloadAsync();
        soundRef.current = null;
        setIsPlayingTts(false);
        return;
      }

      let audioUrl = result.tts_url;
      if (!audioUrl) {
        const textToSpeak = result.spoken_response || `Identified as ${primarySpecies}. Observe closely to confirm.`;
        audioUrl = `/tts?text=${encodeURIComponent(textToSpeak)}`;
      }

      const fullUrl = audioUrl.startsWith('http') ? audioUrl : `${getApiBaseUrl()}${audioUrl}`;
      if (!AudioModule) {
        console.log('Audio playback not supported in Expo Go SDK 57 sandbox. Stream URL:', fullUrl);
        return;
      }
      setIsPlayingTts(true);
      const { sound } = await AudioModule.Sound.createAsync(
        { uri: fullUrl },
        { shouldPlay: true }
      );
      soundRef.current = sound;
      sound.setOnPlaybackStatusUpdate((status: any) => {
        if (status.isLoaded && status.didJustFinish) {
          setIsPlayingTts(false);
          soundRef.current = null;
        }
      });
    } catch (err) {
      console.log('TTS playback error:', err);
      setIsPlayingTts(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Text style={styles.backBtnText}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Identification</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {result.transcription ? (
          <View style={styles.voiceQueryPill}>
            <Text style={styles.voiceQueryLabel}>HEARD ALOUD</Text>
            <Text style={styles.voiceQueryText}>&ldquo;{result.transcription}&rdquo;</Text>
          </View>
        ) : null}

        {/* Species Name & Scientific Name */}
        <View style={styles.speciesHeader}>
          <Text style={styles.speciesName}>{primarySpecies}</Text>
          {sciName ? <Text style={styles.sciName}>{sciName}</Text> : null}
        </View>

        {/* Spoken Advice Audio Button */}
        <TouchableOpacity
          style={styles.ttsButton}
          onPress={handlePlayTts}
          activeOpacity={0.8}
        >
          <Text style={styles.ttsButtonIcon}>{isPlayingTts ? '⏹' : '🔊'}</Text>
          <Text style={styles.ttsButtonText}>
            {isPlayingTts ? 'Stop Voice' : 'Listen to Spoken Advice'}
          </Text>
        </TouchableOpacity>

        {/* Confidence Badge & Bar */}
        <View style={styles.confidenceBox}>
          <View style={styles.confidenceRow}>
            <View style={[styles.badge, styles[`badge_${confidenceLevel}`]]}>
              <Text style={styles[`badgeText_${confidenceLevel}`]}>
                {confidenceLevel.toUpperCase()} CONFIDENCE
              </Text>
            </View>
            <Text style={styles.confidencePercent}>{confidencePercent}%</Text>
          </View>
          <View style={styles.barBackground}>
            <View
              style={[
                styles.barFill,
                {
                  width: `${confidencePercent}%`,
                  backgroundColor:
                    confidenceLevel === 'high'
                      ? colors.confidenceHigh
                      : confidenceLevel === 'mid'
                      ? colors.confidenceMid
                      : colors.confidenceLow,
                },
              ]}
            />
          </View>
        </View>

        {/* "Look for" Confirmation Box */}
        <View style={styles.lookForBox}>
          <Text style={styles.metaLabel}>WHAT TO OBSERVE TO CONFIRM</Text>
          <Text style={styles.lookForContent}>{result.response}</Text>
        </View>

        {/* Other Possibilities */}
        {candidates.length > 0 && (
          <View style={styles.candidatesSection}>
            <Text style={styles.metaLabel}>OTHER POSSIBILITIES</Text>
            {candidates.slice(0, 3).map((c, i) => (
              <View key={i} style={styles.candidateRow}>
                <Text style={styles.candidateName}>{c.name}</Text>
                {c.sci ? <Text style={styles.candidateSci}>{c.sci}</Text> : null}
              </View>
            ))}
          </View>
        )}

        {/* Field Notes Input */}
        <View style={styles.notesSection}>
          <Text style={styles.metaLabel}>FIELD NOTES</Text>
          <TextInput
            style={styles.notesInput}
            placeholder="e.g. Near birch canopy, singing repeatedly"
            placeholderTextColor={colors.muted}
            value={userNote}
            onChangeText={setUserNote}
          />
        </View>

        {/* Actions */}
        <View style={styles.actionContainer}>
          <TouchableOpacity
            style={[styles.saveBtn, saved && styles.savedBtn]}
            onPress={handleSave}
            disabled={saved}
          >
            <Text style={styles.saveBtnText}>
              {saved ? 'Saved to Journal' : 'Save to Trail Journal'}
            </Text>
          </TouchableOpacity>

          {!feedbackGiven ? (
            <TouchableOpacity
              style={styles.notRightBtn}
              onPress={() => setFeedbackGiven(true)}
            >
              <Text style={styles.notRightText}>Not right?</Text>
            </TouchableOpacity>
          ) : (
            <Text style={styles.feedbackAck}>
              Noted. Try observing from another angle or recording closer.
            </Text>
          )}
        </View>

        {/* Safety Footnote */}
        <View style={styles.safetyBox}>
          <Text style={styles.safetyText}>
            Do not eat or touch any plant or fungus based on this identification.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.paper,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: layout.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  backBtn: {
    paddingVertical: spacing.xs,
  },
  backBtnText: {
    fontSize: typography.sizeBase,
    color: colors.ink,
    fontWeight: '500',
  },
  headerTitle: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
    textTransform: 'uppercase',
  },
  scrollContent: {
    padding: spacing.lg,
    gap: spacing.lg,
  },
  speciesHeader: {
    gap: spacing.xs,
  },
  speciesName: {
    fontFamily: typography.fontSerif,
    fontSize: typography.size2xl,
    fontWeight: '600',
    color: colors.ink,
  },
  sciName: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeSm,
    color: colors.muted,
    fontStyle: 'italic',
  },
  ttsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: 'rgba(79, 107, 58, 0.12)',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: layout.borderRadius,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.moss,
    alignSelf: 'flex-start',
  },
  ttsButtonIcon: {
    fontSize: typography.sizeBase,
  },
  ttsButtonText: {
    fontSize: typography.sizeSm,
    color: colors.moss,
    fontWeight: '600',
  },
  confidenceBox: {
    gap: spacing.xs,
  },
  confidenceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  badge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: layout.borderRadius,
  },
  badge_high: {
    backgroundColor: 'rgba(79, 107, 58, 0.1)',
  },
  badge_mid: {
    backgroundColor: 'rgba(166, 139, 58, 0.1)',
  },
  badge_low: {
    backgroundColor: 'rgba(139, 74, 58, 0.1)',
  },
  badgeText_high: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.confidenceHigh,
  },
  badgeText_mid: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.confidenceMid,
  },
  badgeText_low: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.confidenceLow,
  },
  confidencePercent: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
  barBackground: {
    height: 4,
    backgroundColor: colors.divider,
    borderRadius: 2,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 2,
  },
  lookForBox: {
    backgroundColor: colors.overlay,
    borderLeftWidth: 3,
    borderLeftColor: colors.moss,
    padding: spacing.md,
    borderRadius: layout.borderRadius,
    gap: spacing.xs,
  },
  metaLabel: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
    letterSpacing: 0.5,
  },
  lookForContent: {
    fontSize: typography.sizeBase,
    lineHeight: 22,
    color: colors.ink,
  },
  candidatesSection: {
    gap: spacing.xs,
  },
  candidateRow: {
    paddingVertical: spacing.sm,
    borderBottomWidth: layout.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  candidateName: {
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeBase,
    color: colors.ink,
  },
  candidateSci: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
  notesSection: {
    gap: spacing.xs,
  },
  notesInput: {
    borderWidth: layout.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.overlay,
    borderRadius: layout.borderRadius,
    padding: spacing.md,
    fontSize: typography.sizeSm,
    color: colors.ink,
  },
  actionContainer: {
    alignItems: 'center',
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  saveBtn: {
    backgroundColor: colors.moss,
    width: '100%',
    paddingVertical: spacing.md,
    borderRadius: layout.borderRadius,
    alignItems: 'center',
  },
  savedBtn: {
    backgroundColor: colors.mossDark,
  },
  saveBtnText: {
    color: colors.paper,
    fontSize: typography.sizeBase,
    fontWeight: '600',
  },
  notRightBtn: {
    padding: spacing.xs,
  },
  notRightText: {
    fontSize: typography.sizeSm,
    color: colors.muted,
  },
  feedbackAck: {
    fontSize: typography.sizeXs,
    color: colors.muted,
    fontStyle: 'italic',
  },
  safetyBox: {
    borderWidth: layout.hairlineWidth,
    borderColor: 'rgba(139, 58, 58, 0.25)',
    padding: spacing.sm,
    borderRadius: layout.borderRadius,
  },
  safetyText: {
    fontSize: typography.sizeXs,
    color: colors.error,
    textAlign: 'center',
  },
  voiceQueryPill: {
    backgroundColor: 'rgba(79, 107, 58, 0.08)',
    borderLeftWidth: 3,
    borderLeftColor: colors.moss,
    padding: spacing.sm,
    borderRadius: layout.borderRadius,
    gap: 2,
  },
  voiceQueryLabel: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.moss,
    letterSpacing: 0.5,
  },
  voiceQueryText: {
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeSm,
    color: colors.ink,
    fontStyle: 'italic',
  },
});
