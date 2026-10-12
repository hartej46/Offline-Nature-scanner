import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  TextInput,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import { colors, spacing, typography, layout } from '../styles/theme';
import { identifyText, identifyPhoto, identifyPhotoUri, getModelPackStatus } from '../services/api';
import type { IdentifyResponse } from '../services/api';
import ModelPackModal from '../components/ModelPackModal';


interface HomeScreenProps {
  onStartListening: () => void;
  onShowResult: (result: IdentifyResponse) => void;
  onNavigateJournal: () => void;
}

export default function HomeScreen({
  onStartListening,
  onShowResult,
  onNavigateJournal,
}: HomeScreenProps) {
  const [loading, setLoading] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [showTextInput, setShowTextInput] = useState(false);
  const [showModelPackModal, setShowModelPackModal] = useState(false);
  const [modelStatus, setModelStatus] = useState<any>(null);

  const refreshModelStatus = async () => {
    try {
      const FileSystem = await import('expo-file-system/legacy');
      const baseDir = FileSystem.documentDirectory || '';
      const e2bInfo = await FileSystem.getInfoAsync(`${baseDir}models/gemma4-e2b.gguf`);
      const e4bInfo = await FileSystem.getInfoAsync(`${baseDir}models/gemma4-e4b.gguf`);

      const e2bBytes = e2bInfo.exists ? (e2bInfo as any).size || 0 : 0;
      const e4bBytes = e4bInfo.exists ? (e4bInfo as any).size || 0 : 0;

      // Gemma weights byte thresholds:
      // E2B expected 2,019,377,376 bytes. Verified complete if >= 2,000,000,000 bytes.
      // E4B expected 9,608,338,848 bytes. Verified complete if >= 9,000,000,000 bytes.
      const isCompleteE2B = e2bBytes >= 2000000000;
      const isCompleteE4B = e4bBytes >= 9000000000;

      const isIncompleteE2B = !isCompleteE2B && e2bBytes > 0;
      const isIncompleteE4B = !isCompleteE4B && e4bBytes > 0;

      if (isCompleteE4B || isCompleteE2B) {
        const activeName = isCompleteE4B ? 'Google Gemma 4 E4B' : 'Google Gemma 4 E2B';
        const activeSize = isCompleteE4B ? '9.0 GB' : '1.9 GB';
        setModelStatus({
          is_installed: true,
          is_incomplete: false,
          name: activeName,
          size_formatted: activeSize,
        });
      } else if (isIncompleteE4B || isIncompleteE2B) {
        const partialName = isIncompleteE4B ? 'Google Gemma 4 E4B' : 'Google Gemma 4 E2B';
        const partialBytes = isIncompleteE4B ? e4bBytes : e2bBytes;
        const targetBytes = isIncompleteE4B ? 9608338848 : 2019377376;
        const targetFormatted = isIncompleteE4B ? '9.0 GB' : '1.9 GB';
        const partialMB = (partialBytes / (1024 * 1024)).toFixed(0);
        const pct = Math.min(99, Math.round((partialBytes / targetBytes) * 100));

        setModelStatus({
          is_installed: false,
          is_incomplete: true,
          name: partialName,
          partial_formatted: `${partialMB} MB`,
          target_formatted: targetFormatted,
          pct,
        });
      } else {
        setModelStatus({
          is_installed: false,
          is_incomplete: false,
          name: 'No Model Installed',
          size_formatted: '0 B',
        });
      }
    } catch {
      setModelStatus(null);
    }
  };

  useEffect(() => {
    refreshModelStatus();
  }, []);



  const handleTextSubmit = async () => {
    if (!textInput.trim()) return;
    setLoading(true);
    try {
      const res = await identifyText(textInput);
      onShowResult(res);
      setTextInput('');
      setShowTextInput(false);
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Identification failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePhotoIdentify = async () => {
    try {
      const permission = await ImagePicker.requestCameraPermissionsAsync();
      let result: ImagePicker.ImagePickerResult;
      if (permission.granted) {
        result = await ImagePicker.launchCameraAsync({
          allowsEditing: true,
          aspect: [4, 3],
          quality: 0.8,
          base64: true,
        });
      } else {
        const libPerm = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!libPerm.granted) {
          Alert.alert('Permission Needed', 'Please allow camera or photo library access to photograph species.');
          return;
        }
        result = await ImagePicker.launchImageLibraryAsync({
          allowsEditing: true,
          aspect: [4, 3],
          quality: 0.8,
          base64: true,
        });
      }

      if (!result.canceled && result.assets && result.assets.length > 0) {
        setLoading(true);
        const asset = result.assets[0];
        const res = await identifyPhoto({
          uri: asset.uri,
          base64: asset.base64 || undefined,
        });
        onShowResult(res);
      }
    } catch (err) {
      Alert.alert('Photo Error', err instanceof Error ? err.message : 'Identification failed');
    } finally {
      setLoading(false);
    }
  };


  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Field Companion</Text>
          <View style={styles.statusRow}>
            <View
              style={[
                styles.statusDot,
                modelStatus?.is_incomplete && { backgroundColor: '#F59E0B' },
                !modelStatus?.is_installed &&
                  !modelStatus?.is_incomplete && { backgroundColor: '#9CA3AF' },
              ]}
            />
            <Text
              style={[
                styles.statusText,
                modelStatus?.is_incomplete && { color: '#B45309' },
                !modelStatus?.is_installed &&
                  !modelStatus?.is_incomplete && { color: '#6B7280' },
              ]}
            >
              {modelStatus?.is_installed
                ? 'Offline ready'
                : modelStatus?.is_incomplete
                ? 'Model incomplete'
                : 'Server mode'}
            </Text>
          </View>
        </View>

        {/* On-Device Gemma 4 Model Selector Banner */}
        <TouchableOpacity
          style={[
            styles.modelPackPill,
            modelStatus?.is_incomplete && styles.modelPackPillIncomplete,
          ]}
          onPress={() => setShowModelPackModal(true)}
          activeOpacity={0.8}
        >
          <View style={styles.modelPackLeft}>
            <Text style={styles.modelPackIcon}>
              {modelStatus?.is_incomplete ? '⚠️' : '📦'}
            </Text>
            <Text
              style={[
                styles.modelPackLabel,
                modelStatus?.is_incomplete && { color: '#92400E', fontWeight: '600' },
              ]}
            >
              {modelStatus?.is_installed
                ? `${modelStatus.name}: Active`
                : modelStatus?.is_incomplete
                ? `${modelStatus.name}: Incomplete (${modelStatus.partial_formatted} / ${modelStatus.target_formatted})`
                : 'On-Device Model: None installed'}
            </Text>
          </View>
          <View
            style={[
              styles.modelPackBadge,
              modelStatus?.is_incomplete && styles.modelPackBadgeIncomplete,
              !modelStatus?.is_installed &&
                !modelStatus?.is_incomplete &&
                styles.modelPackBadgeEmpty,
            ]}
          >
            <Text
              style={[
                styles.modelPackBadgeText,
                modelStatus?.is_incomplete && styles.modelPackBadgeTextIncomplete,
              ]}
            >
              {modelStatus?.is_installed
                ? `${modelStatus.size_formatted} • Change`
                : modelStatus?.is_incomplete
                ? `Resume / Fix (${modelStatus.pct}%)`
                : 'Install E2B / E4B'}
            </Text>
          </View>
        </TouchableOpacity>


        {/* Center prompt */}
        <View style={styles.centerSection}>
          <Text style={styles.prompt}>What did you find?</Text>
          <Text style={styles.subprompt}>
            Listen to a call, capture a photo, or describe what you observed.
          </Text>

          {showTextInput && (
            <View style={styles.textQueryBox}>
              <TextInput
                style={styles.textInput}
                placeholder="e.g. Small black bird with white wing patch"
                placeholderTextColor={colors.muted}
                value={textInput}
                onChangeText={setTextInput}
                onSubmitEditing={handleTextSubmit}
                returnKeyType="search"
              />
              <TouchableOpacity
                style={styles.textSubmitBtn}
                onPress={handleTextSubmit}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color={colors.paper} size="small" />
                ) : (
                  <Text style={styles.textSubmitBtnText}>Identify</Text>
                )}
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Primary Action Buttons (Thumb zone) */}
        <View style={styles.actionSection}>
          <TouchableOpacity
            style={[styles.actionBtn, styles.listenBtn]}
            onPress={onStartListening}
            activeOpacity={0.8}
          >
            <Text style={styles.listenBtnText}>Listen</Text>
            <Text style={styles.btnSubtext}>Record bird or nature sound</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionBtn, styles.photoBtn]}
            onPress={handlePhotoIdentify}
            activeOpacity={0.8}
            disabled={loading}
          >
            <Text style={styles.photoBtnText}>Photograph</Text>
            <Text style={styles.btnSubtextDark}>Capture plant, flower, or insect</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.describeToggleBtn}
            onPress={() => setShowTextInput(!showTextInput)}
          >
            <Text style={styles.describeToggleText}>
              {showTextInput ? 'Hide text description' : 'Describe observation with text'}
            </Text>
          </TouchableOpacity>

          {/* Plant Safety Footnote */}
          <View style={styles.safetyBox}>
            <Text style={styles.safetyText}>
              Do not eat or touch any plant or fungus based on this identification.
            </Text>
          </View>
        </View>
      </View>

      <ModelPackModal
        visible={showModelPackModal}
        onClose={() => setShowModelPackModal(false)}
        onModelChanged={refreshModelStatus}
      />

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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.md,
    borderBottomWidth: layout.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  title: {
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeXl,
    fontWeight: '600',
    color: colors.ink,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.moss,
    marginRight: spacing.xs,
  },
  statusText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
    textTransform: 'uppercase',
  },
  centerSection: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  prompt: {
    fontFamily: typography.fontSerif,
    fontSize: typography.size2xl,
    color: colors.ink,
    textAlign: 'center',
    marginBottom: spacing.xs,
  },
  subprompt: {
    fontSize: typography.sizeSm,
    color: colors.muted,
    textAlign: 'center',
    maxWidth: 280,
  },
  textQueryBox: {
    width: '100%',
    marginTop: spacing.lg,
  },
  textInput: {
    borderWidth: layout.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.overlay,
    borderRadius: layout.borderRadius,
    padding: spacing.md,
    fontSize: typography.sizeBase,
    color: colors.ink,
  },
  textSubmitBtn: {
    backgroundColor: colors.moss,
    marginTop: spacing.sm,
    padding: spacing.md,
    borderRadius: layout.borderRadius,
    alignItems: 'center',
  },
  textSubmitBtnText: {
    color: colors.paper,
    fontWeight: '600',
    fontSize: typography.sizeBase,
  },
  actionSection: {
    gap: spacing.md,
    paddingBottom: spacing.lg,
  },
  actionBtn: {
    width: '100%',
    borderRadius: layout.borderRadius,
    alignItems: 'center',
    justifyContent: 'center',
  },
  listenBtn: {
    backgroundColor: colors.moss,
    minHeight: 72,
    paddingVertical: spacing.md,
  },
  listenBtnText: {
    color: colors.paper,
    fontFamily: typography.fontSerif,
    fontSize: typography.size2xl,
    fontWeight: '600',
  },
  btnSubtext: {
    color: colors.paper,
    opacity: 0.8,
    fontSize: typography.sizeXs,
    marginTop: 2,
  },
  photoBtn: {
    backgroundColor: 'transparent',
    borderWidth: layout.hairlineWidth,
    borderColor: colors.divider,
    minHeight: 56,
    paddingVertical: spacing.sm,
  },
  photoBtnText: {
    color: colors.ink,
    fontSize: typography.sizeLg,
    fontWeight: '500',
    fontFamily: typography.fontSerif,
  },
  btnSubtextDark: {
    color: colors.muted,
    fontSize: typography.sizeXs,
    marginTop: 2,
  },
  describeToggleBtn: {
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  describeToggleText: {
    fontSize: typography.sizeSm,
    color: colors.moss,
    textDecorationLine: 'underline',
  },
  safetyBox: {
    borderWidth: layout.hairlineWidth,
    borderColor: 'rgba(139, 58, 58, 0.25)',
    padding: spacing.sm,
    borderRadius: layout.borderRadius,
    marginTop: spacing.xs,
  },
  safetyText: {
    fontSize: typography.sizeXs,
    color: colors.error,
    textAlign: 'center',
  },
  modelPackPill: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(79, 107, 58, 0.08)',
    borderWidth: layout.hairlineWidth,
    borderColor: 'rgba(79, 107, 58, 0.3)',
    borderRadius: 20,
    paddingVertical: 6,
    paddingHorizontal: spacing.sm,
    marginVertical: spacing.xs,
  },
  modelPackLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  modelPackIcon: {
    fontSize: typography.sizeSm,
  },
  modelPackLabel: {
    fontFamily: typography.fontSans,
    fontSize: typography.sizeXs,
    color: colors.ink,
    fontWeight: '500',
  },
  modelPackBadge: {
    backgroundColor: colors.moss,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  modelPackBadgeEmpty: {
    backgroundColor: colors.muted,
  },

  modelPackBadgeText: {
    fontFamily: typography.fontMono,
    fontSize: 10,
    color: colors.paper,
    fontWeight: '600',
  },
  modelPackPillIncomplete: {
    backgroundColor: '#FFFBEB',
    borderColor: '#F59E0B',
    borderWidth: 1,
  },
  modelPackBadgeIncomplete: {
    backgroundColor: '#FDE68A',
    borderColor: '#F59E0B',
    borderWidth: layout.hairlineWidth,
  },
  modelPackBadgeTextIncomplete: {
    color: '#92400E',
    fontWeight: '700',
  },
});

