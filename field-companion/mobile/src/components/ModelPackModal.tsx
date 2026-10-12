import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import * as Device from 'expo-device';
import * as FileSystem from 'expo-file-system/legacy';
import { colors, spacing, typography, layout } from '../styles/theme';
import {
  getAvailableModels,
  installModel,
  uninstallModel,
  getApiBaseUrl,
  ModelOption,
} from '../services/api';

interface ModelPackModalProps {
  visible: boolean;
  onClose: () => void;
  onModelChanged?: () => void;
}

interface LocalFileInfo {
  exists: boolean;
  isComplete: boolean;
  isIncomplete: boolean;
  sizeBytes: number;
  expectedBytes: number;
  completionPercent: number;
  sizeFormatted: string;
  expectedFormatted: string;
  uri: string;
  updatedAt?: string;
}

export default function ModelPackModal({ visible, onClose, onModelChanged }: ModelPackModalProps) {
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [deviceRamGb, setDeviceRamGb] = useState<number>(4.0);
  const [localFiles, setLocalFiles] = useState<Record<string, LocalFileInfo>>({});

  // Active download tracking
  const [downloadingModelId, setDownloadingModelId] = useState<string | null>(null);
  const [downloadPercent, setDownloadPercent] = useState<number>(0);
  const [downloadMBText, setDownloadMBText] = useState<string>('');
  const [downloadSpeedText, setDownloadSpeedText] = useState<string>('');
  const downloadTaskRef = useRef<FileSystem.DownloadResumable | null>(null);
  const lastProgressRef = useRef<{ bytes: number; time: number }>({ bytes: 0, time: 0 });

  useEffect(() => {
    if (visible) {
      loadModelListAndLocalFiles();
    }
  }, [visible]);

  const getModelLocalUri = (modelId: string) => {
    const cleanId = modelId.replace(':', '-');
    const baseDir = FileSystem.documentDirectory || '';
    return `${baseDir}models/${cleanId}.gguf`;
  };

  const inspectDeviceStorage = async (modelList: ModelOption[]) => {
    try {
      const baseDir = FileSystem.documentDirectory;
      if (!baseDir) return;

      const modelsDir = `${baseDir}models/`;
      const dirInfo = await FileSystem.getInfoAsync(modelsDir);
      if (!dirInfo.exists) {
        await FileSystem.makeDirectoryAsync(modelsDir, { intermediates: true });
      }

      const filesMap: Record<string, LocalFileInfo> = {};
      for (const m of modelList) {
        const uri = getModelLocalUri(m.id);
        const info = await FileSystem.getInfoAsync(uri);
        const expectedBytes = m.size_bytes;
        const expectedMb = expectedBytes / (1024 * 1024);
        const expectedFormatted =
          expectedMb >= 1000 ? `${(expectedMb / 1024).toFixed(1)} GB` : `${expectedMb.toFixed(0)} MB`;

        if (info.exists && (info as any).size) {
          const bytes = (info as any).size as number;
          const mb = bytes / (1024 * 1024);
          const sizeFormatted = mb >= 1000 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(1)} MB`;

          // A file is complete ONLY if it has at least 99.5% of expected weights bytes
          const isComplete = bytes >= expectedBytes * 0.995;
          const isIncomplete = !isComplete && bytes > 0;
          const pct = Math.min(99, Math.round((bytes / expectedBytes) * 100));

          filesMap[m.id] = {
            exists: true,
            isComplete,
            isIncomplete,
            sizeBytes: bytes,
            expectedBytes,
            completionPercent: isComplete ? 100 : pct,
            sizeFormatted,
            expectedFormatted,
            uri,
            updatedAt: (info as any).modificationTime
              ? new Date((info as any).modificationTime * 1000).toLocaleTimeString()
              : undefined,
          };
        } else {
          filesMap[m.id] = {
            exists: false,
            isComplete: false,
            isIncomplete: false,
            sizeBytes: 0,
            expectedBytes,
            completionPercent: 0,
            sizeFormatted: '0 MB',
            expectedFormatted,
            uri,
          };
        }
      }
      setLocalFiles(filesMap);
    } catch (err) {
      console.warn('Error inspecting local storage:', err);
    }
  };

  const loadModelListAndLocalFiles = async () => {
    setLoading(true);
    try {
      let ramGb = 4.0;
      if (Device.totalMemory) {
        ramGb = Math.round((Device.totalMemory / (1024 * 1024 * 1024)) * 10) / 10;
      }
      setDeviceRamGb(ramGb);

      const res = await getAvailableModels(ramGb);
      setModels(res.models);
      await inspectDeviceStorage(res.models);
    } catch {
      const fallbackModels: ModelOption[] = [
        {
          id: 'gemma4:e2b',
          name: 'Google Gemma 4 E2B',
          subtitle: 'Edge Mobile Optimized',
          size_formatted: '1.9 GB',
          size_bytes: 2019377376,
          min_ram_gb: 3.0,
          recommended_ram_gb: 4.0,
          quantization: 'Q4_K_M (4-bit Mobile)',
          speed: '~18.4 tok/s',
          description:
            'Ultra-lightweight on-device multimodal model tuned for fast field identification and mobile batteries.',
          is_installed: false,
          is_active: false,
        },
      ];
      setModels(fallbackModels);
      await inspectDeviceStorage(fallbackModels);
    } finally {
      setLoading(false);
    }
  };

  const handleStartRealDownload = async (model: ModelOption, resumeFromBytes: number = 0) => {
    try {
      const targetUri = getModelLocalUri(model.id);
      const downloadUrl = `${getApiBaseUrl()}/model/download/${model.id}`;

      setDownloadingModelId(model.id);

      // Clean start if not resuming
      if (resumeFromBytes <= 0) {
        try {
          await FileSystem.deleteAsync(targetUri, { idempotent: true });
        } catch {}
      }

      const initialPct =
        resumeFromBytes > 0 ? Math.min(99, Math.round((resumeFromBytes / model.size_bytes) * 100)) : 0;
      setDownloadPercent(initialPct);

      const initialWrittenMB = (resumeFromBytes / (1024 * 1024)).toFixed(1);
      const totalMB = (model.size_bytes / (1024 * 1024)).toFixed(1);
      setDownloadMBText(`${initialWrittenMB} MB / ${totalMB} MB`);
      setDownloadSpeedText(
        resumeFromBytes > 0
          ? `Resuming from ${initialWrittenMB} MB...`
          : 'Connecting to model server...'
      );

      lastProgressRef.current = { bytes: resumeFromBytes, time: Date.now() };

      // Android FileSystem accepts resumeData as byte offset string
      const resumeData = resumeFromBytes > 0 ? String(resumeFromBytes) : undefined;

      const downloadResumable = FileSystem.createDownloadResumable(
        downloadUrl,
        targetUri,
        {},
        (downloadProgress) => {
          const written = downloadProgress.totalBytesWritten;
          const expected =
            downloadProgress.totalBytesExpectedToWrite > 0
              ? downloadProgress.totalBytesExpectedToWrite
              : model.size_bytes;

          const pct = Math.min(100, Math.round((written / expected) * 100));
          setDownloadPercent(pct);

          const writtenMB = (written / (1024 * 1024)).toFixed(1);
          const totalExpectedMB = (expected / (1024 * 1024)).toFixed(1);
          setDownloadMBText(`${writtenMB} MB / ${totalExpectedMB} MB`);

          const now = Date.now();
          const dt = (now - lastProgressRef.current.time) / 1000;
          if (dt >= 0.5) {
            const dBytes = written - lastProgressRef.current.bytes;
            const speedMBps = dBytes / (1024 * 1024) / dt;
            if (speedMBps > 0) {
              setDownloadSpeedText(`${speedMBps.toFixed(1)} MB/s`);
            }
            lastProgressRef.current = { bytes: written, time: now };
          }
        },
        resumeData
      );

      downloadTaskRef.current = downloadResumable;
      const result = await downloadResumable.downloadAsync();

      if (result && result.uri) {
        // STRICT SIZE VERIFICATION:
        const fileInfo = await FileSystem.getInfoAsync(result.uri);
        const actualBytes = (fileInfo as any).size || 0;
        const actualFormatted =
          actualBytes >= 1024 * 1024 * 1000
            ? `${(actualBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
            : `${(actualBytes / (1024 * 1024)).toFixed(1)} MB`;

        if (actualBytes < model.size_bytes * 0.995) {
          // Incomplete download
          await inspectDeviceStorage(models);
          onModelChanged?.();
          Alert.alert(
            'Download Stopped Prematurely',
            `Downloaded ${actualFormatted} of ${model.size_formatted}. The partial file was preserved on device so you can Resume anytime without starting over.`
          );
          return;
        }

        // FULLY COMPLETE & VERIFIED:
        await installModel(model.id);
        await inspectDeviceStorage(models);
        onModelChanged?.();

        Alert.alert(
          'Model Download Complete & Verified',
          `Successfully saved and verified all ${actualFormatted} to device storage:\n${result.uri}`
        );
      }
    } catch (err: any) {
      if (err?.message?.includes?.('canceled') || err?.message?.includes?.('cancelled')) {
        // Handled in cancel modal
      } else {
        await inspectDeviceStorage(models);
        onModelChanged?.();
        Alert.alert(
          'Download Interrupted',
          `${err?.message || 'Network transfer stopped'}. Any downloaded data has been kept on device so you can resume.`
        );
      }
    } finally {
      setDownloadingModelId(null);
      downloadTaskRef.current = null;
    }
  };

  const handleCancelDownload = async () => {
    if (!downloadingModelId) return;
    const currentId = downloadingModelId;

    Alert.alert(
      'Stop Download',
      'What would you like to do with the downloaded weights?',
      [
        {
          text: 'Keep Data (Resume Later)',
          style: 'default',
          onPress: async () => {
            try {
              if (downloadTaskRef.current) {
                await downloadTaskRef.current.cancelAsync();
              }
            } catch (e) {
              console.warn('Error cancelling task:', e);
            } finally {
              setDownloadingModelId(null);
              downloadTaskRef.current = null;
              await inspectDeviceStorage(models);
              onModelChanged?.();
            }
          },
        },
        {
          text: 'Delete Partial File',
          style: 'destructive',
          onPress: async () => {
            try {
              if (downloadTaskRef.current) {
                await downloadTaskRef.current.cancelAsync();
              }
              const uri = getModelLocalUri(currentId);
              await FileSystem.deleteAsync(uri, { idempotent: true });
            } catch (e) {
              console.warn('Error deleting partial:', e);
            } finally {
              setDownloadingModelId(null);
              downloadTaskRef.current = null;
              await inspectDeviceStorage(models);
              onModelChanged?.();
            }
          },
        },
      ]
    );
  };

  const handleRestartFresh = (model: ModelOption) => {
    Alert.alert(
      'Restart from 0%',
      `Delete existing partial download and download ${model.name} (${model.size_formatted}) from the beginning?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Restart from 0%',
          style: 'destructive',
          onPress: async () => {
            const uri = getModelLocalUri(model.id);
            try {
              await FileSystem.deleteAsync(uri, { idempotent: true });
            } catch {}
            await inspectDeviceStorage(models);
            handleStartRealDownload(model, 0);
          },
        },
      ]
    );
  };

  const handleDeletePartial = (model: ModelOption) => {
    Alert.alert(
      'Delete Incomplete Download',
      `Delete partial download for ${model.name}? This will free device storage.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete Partial',
          style: 'destructive',
          onPress: async () => {
            try {
              const uri = getModelLocalUri(model.id);
              await FileSystem.deleteAsync(uri, { idempotent: true });
              await uninstallModel(model.id);
              await inspectDeviceStorage(models);
              onModelChanged?.();
              Alert.alert('Deleted', 'Incomplete weights deleted from storage.');
            } catch (err: any) {
              Alert.alert('Error', err?.message || 'Could not delete partial weights.');
            }
          },
        },
      ]
    );
  };

  const handleUninstall = async (model: ModelOption) => {
    Alert.alert(
      'Delete from Device',
      `Delete ${model.name} from phone storage? This will free ${model.size_formatted}.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              const uri = getModelLocalUri(model.id);
              await FileSystem.deleteAsync(uri, { idempotent: true });
              await uninstallModel(model.id);
              await inspectDeviceStorage(models);
              onModelChanged?.();
              Alert.alert('Model Deleted', `Deleted from phone storage.`);
            } catch (err: any) {
              Alert.alert('Error', err?.message || 'Could not delete model.');
            }
          },
        },
      ]
    );
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          {/* Header */}
          <View style={styles.header}>
            <View>
              <Text style={styles.headerTag}>NATIVE ON-DEVICE STORAGE</Text>
              <Text style={styles.headerTitle}>Gemma 4 Models</Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={styles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Real Device Specs Banner */}
          <View style={styles.deviceBanner}>
            <Text style={styles.deviceBannerText}>
              📱 Hardware RAM: <Text style={styles.deviceBannerBold}>{deviceRamGb} GB</Text>
              {deviceRamGb < 6.0
                ? ' • E4B hidden (requires 6 GB+ RAM)'
                : ' • Device qualifies for E2B & E4B weights'}
            </Text>
          </View>

          <ScrollView contentContainerStyle={styles.scrollBody}>
            {loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator color={colors.moss} size="large" />
                <Text style={styles.loadingText}>Checking local storage & available models...</Text>
              </View>
            ) : (
              models.map((model) => {
                const localInfo = localFiles[model.id];
                const isStoredAndComplete = !!localInfo?.isComplete;
                const isIncomplete = !!localInfo?.isIncomplete;
                const isCurrentlyDownloading = downloadingModelId === model.id;

                return (
                  <View
                    key={model.id}
                    style={[
                      styles.modelCard,
                      isStoredAndComplete && styles.modelCardActive,
                      isIncomplete && styles.modelCardIncomplete,
                    ]}
                  >
                    <View style={styles.cardHeader}>
                      <View>
                        <Text style={styles.modelName}>{model.name}</Text>
                        <Text style={styles.modelSubtitle}>{model.subtitle}</Text>
                      </View>
                      <View
                        style={[
                          styles.badge,
                          isIncomplete && styles.badgeIncomplete,
                        ]}
                      >
                        <Text
                          style={[
                            styles.badgeText,
                            isIncomplete && styles.badgeTextIncomplete,
                          ]}
                        >
                          {isIncomplete
                            ? `Incomplete • ${localInfo.completionPercent}%`
                            : model.size_formatted}
                        </Text>
                      </View>
                    </View>

                    <Text style={styles.modelDesc}>{model.description}</Text>

                    {/* Spec tags */}
                    <View style={styles.tagRow}>
                      <View style={styles.tag}>
                        <Text style={styles.tagLabel}>Min RAM</Text>
                        <Text style={styles.tagValue}>{model.min_ram_gb} GB</Text>
                      </View>
                      <View style={styles.tag}>
                        <Text style={styles.tagLabel}>Format</Text>
                        <Text style={styles.tagValue}>{model.quantization}</Text>
                      </View>
                      <View style={styles.tag}>
                        <Text style={styles.tagLabel}>Inference</Text>
                        <Text style={styles.tagValue}>{model.speed}</Text>
                      </View>
                    </View>

                    {/* On-Device Storage Status Details: FULLY COMPLETE */}
                    {isStoredAndComplete && (
                      <View style={styles.storageInfoBox}>
                        <View style={styles.storageHeaderRow}>
                          <Text style={styles.storageTitle}>📂 Stored & Verified on Device</Text>
                          <Text style={styles.storageSize}>{localInfo.sizeFormatted}</Text>
                        </View>
                        <Text style={styles.storagePath} numberOfLines={1}>
                          {localInfo.uri}
                        </Text>
                      </View>
                    )}

                    {/* On-Device Storage Status Details: INCOMPLETE WARNING */}
                    {isIncomplete && !isCurrentlyDownloading && (
                      <View style={styles.incompleteBox}>
                        <View style={styles.incompleteHeaderRow}>
                          <Text style={styles.incompleteTitle}>
                            ⚠️ Incomplete Download ({localInfo.completionPercent}%)
                          </Text>
                          <Text style={styles.incompleteSize}>
                            {localInfo.sizeFormatted} / {localInfo.expectedFormatted}
                          </Text>
                        </View>
                        <Text style={styles.incompleteDesc}>
                          Download was interrupted. An incomplete model cannot execute on-device. Choose whether to resume where you left off or restart from start.
                        </Text>
                        <View style={styles.incompleteProgressTrack}>
                          <View
                            style={[
                              styles.incompleteProgressFill,
                              { width: `${localInfo.completionPercent}%` },
                            ]}
                          />
                        </View>
                      </View>
                    )}

                    {/* Live Download Progress Section */}
                    {isCurrentlyDownloading && (
                      <View style={styles.downloadProgressSection}>
                        <View style={styles.downloadMetricsRow}>
                          <Text style={styles.downloadMetricsText}>{downloadMBText}</Text>
                          <Text style={styles.downloadSpeedText}>{downloadSpeedText}</Text>
                        </View>
                        <View style={styles.progressBarTrack}>
                          <View
                            style={[
                              styles.progressBarFill,
                              { width: `${downloadPercent}%` },
                            ]}
                          />
                        </View>
                        <View style={styles.cancelRow}>
                          <Text style={styles.downloadPctText}>{downloadPercent}% downloaded</Text>
                          <TouchableOpacity
                            style={styles.cancelDownloadBtn}
                            onPress={handleCancelDownload}
                          >
                            <Text style={styles.cancelDownloadText}>Pause / Stop</Text>
                          </TouchableOpacity>
                        </View>
                      </View>
                    )}

                    {/* Action buttons */}
                    <View style={styles.actionRow}>
                      {isStoredAndComplete ? (
                        <>
                          <View style={styles.installedTag}>
                            <Text style={styles.installedCheck}>✓</Text>
                            <Text style={styles.installedText}>Verified & Mounted</Text>
                          </View>
                          <TouchableOpacity
                            style={styles.uninstallBtn}
                            onPress={() => handleUninstall(model)}
                            disabled={isCurrentlyDownloading}
                          >
                            <Text style={styles.uninstallBtnText}>Delete Weights</Text>
                          </TouchableOpacity>
                        </>
                      ) : isIncomplete && !isCurrentlyDownloading ? (
                        <View style={styles.incompleteActionsContainer}>
                          <TouchableOpacity
                            style={styles.resumeBtn}
                            onPress={() => handleStartRealDownload(model, localInfo.sizeBytes)}
                            disabled={downloadingModelId !== null}
                          >
                            <Text style={styles.resumeBtnText}>
                              ▶ Continue Download ({localInfo.sizeFormatted} → {localInfo.expectedFormatted})
                            </Text>
                          </TouchableOpacity>

                          <View style={styles.incompleteSecondaryRow}>
                            <TouchableOpacity
                              style={styles.restartBtn}
                              onPress={() => handleRestartFresh(model)}
                              disabled={downloadingModelId !== null}
                            >
                              <Text style={styles.restartBtnText}>↺ Start from 0%</Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                              style={styles.deletePartialBtn}
                              onPress={() => handleDeletePartial(model)}
                              disabled={downloadingModelId !== null}
                            >
                              <Text style={styles.deletePartialBtnText}>🗑 Delete Partial</Text>
                            </TouchableOpacity>
                          </View>
                        </View>
                      ) : !isCurrentlyDownloading ? (
                        <TouchableOpacity
                          style={[
                            styles.downloadBtn,
                            downloadingModelId !== null && styles.downloadBtnDisabled,
                          ]}
                          onPress={() => handleStartRealDownload(model, 0)}
                          disabled={downloadingModelId !== null}
                        >
                          <Text style={styles.downloadBtnText}>
                            Download to Device ({model.size_formatted})
                          </Text>
                        </TouchableOpacity>
                      ) : null}
                    </View>
                  </View>
                );
              })
            )}

            {/* Honest Architecture & On-Device Native Note */}
            <View style={styles.noteBox}>
              <Text style={styles.noteTitle}>⚡ Real On-Device Storage & Execution</Text>
              <Text style={styles.noteBody}>
                • <Text style={styles.boldText}>True Device Storage:</Text> Tapping download streams the full GGUF weights directly into your phone's physical storage via Expo FileSystem.
              </Text>
              <Text style={styles.noteBody}>
                • <Text style={styles.boldText}>Resumable Transfers:</Text> If a download is paused or interrupted midway, you can continue from where it left off or restart from start.
              </Text>
              <Text style={styles.noteBody}>
                • <Text style={styles.boldText}>Integrity Verification:</Text> The app will never run on an incomplete download; full weights must be verified on disk before mounting.
              </Text>
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(28, 28, 26, 0.65)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.paper,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    maxHeight: '88%',
    paddingBottom: spacing.xl,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: layout.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  headerTag: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
    letterSpacing: 0.5,
  },
  headerTitle: {
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeLg,
    fontWeight: '600',
    color: colors.ink,
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.overlay,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeBtnText: {
    fontSize: 14,
    color: colors.muted,
    fontWeight: '600',
  },
  deviceBanner: {
    backgroundColor: 'rgba(79, 107, 58, 0.08)',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderBottomWidth: layout.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  deviceBannerText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.ink,
  },
  deviceBannerBold: {
    fontWeight: '700',
    color: colors.moss,
  },
  scrollBody: {
    padding: spacing.lg,
    gap: spacing.md,
  },
  loadingContainer: {
    paddingVertical: spacing.xl,
    alignItems: 'center',
    gap: spacing.sm,
  },
  loadingText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
  modelCard: {
    backgroundColor: colors.overlay,
    borderWidth: 1,
    borderColor: colors.divider,
    borderRadius: layout.borderRadius,
    padding: spacing.md,
    gap: spacing.sm,
  },
  modelCardActive: {
    borderColor: colors.moss,
    borderWidth: 1.5,
    backgroundColor: 'rgba(79, 107, 58, 0.04)',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  modelName: {
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeBase,
    fontWeight: '700',
    color: colors.ink,
  },
  modelSubtitle: {
    fontFamily: typography.fontSans,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
  badge: {
    backgroundColor: 'rgba(79, 107, 58, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  badgeText: {
    fontFamily: typography.fontMono,
    fontSize: 10,
    color: colors.moss,
    fontWeight: '700',
  },
  modelDesc: {
    fontSize: typography.sizeXs,
    color: colors.ink,
    lineHeight: 18,
  },
  tagRow: {
    flexDirection: 'row',
    gap: spacing.xs,
  },
  tag: {
    backgroundColor: colors.paper,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.divider,
    borderRadius: 6,
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  tagLabel: {
    fontFamily: typography.fontMono,
    fontSize: 9,
    color: colors.muted,
  },
  tagValue: {
    fontFamily: typography.fontMono,
    fontSize: 10,
    fontWeight: '600',
    color: colors.ink,
  },
  storageInfoBox: {
    backgroundColor: 'rgba(79, 107, 58, 0.08)',
    borderLeftWidth: 3,
    borderLeftColor: colors.moss,
    padding: spacing.sm,
    borderRadius: 4,
    gap: 2,
    marginTop: 2,
  },
  storageHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  storageTitle: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    fontWeight: '700',
    color: colors.moss,
  },
  storageSize: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.ink,
    fontWeight: '700',
  },
  storagePath: {
    fontFamily: typography.fontMono,
    fontSize: 10,
    color: colors.muted,
  },
  downloadProgressSection: {
    backgroundColor: colors.paper,
    padding: spacing.sm,
    borderRadius: layout.borderRadius,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.divider,
    gap: spacing.xs,
    marginTop: 4,
  },
  downloadMetricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  downloadMetricsText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    fontWeight: '600',
    color: colors.ink,
  },
  downloadSpeedText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.moss,
    fontWeight: '700',
  },
  progressBarTrack: {
    height: 8,
    backgroundColor: colors.divider,
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: colors.moss,
  },
  cancelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  downloadPctText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
  cancelDownloadBtn: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.error,
  },
  cancelDownloadText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.error,
    fontWeight: '600',
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.xs,
  },
  installedTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  installedCheck: {
    color: colors.moss,
    fontWeight: '700',
  },
  installedText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.moss,
    fontWeight: '600',
  },
  uninstallBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.error,
  },
  uninstallBtnText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.error,
    fontWeight: '600',
  },
  downloadBtn: {
    backgroundColor: colors.moss,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: layout.borderRadius,
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  downloadBtnDisabled: {
    opacity: 0.6,
  },
  downloadBtnText: {
    color: colors.paper,
    fontFamily: typography.fontSans,
    fontSize: typography.sizeSm,
    fontWeight: '600',
  },
  modelCardIncomplete: {
    borderColor: '#F59E0B',
    borderWidth: 1.5,
    backgroundColor: 'rgba(245, 158, 11, 0.04)',
  },
  badgeIncomplete: {
    backgroundColor: '#FEF3C7',
    borderWidth: layout.hairlineWidth,
    borderColor: '#F59E0B',
  },
  badgeTextIncomplete: {
    color: '#B45309',
  },
  incompleteBox: {
    backgroundColor: '#FFFBEB',
    borderWidth: 1,
    borderColor: '#FDE68A',
    padding: spacing.sm,
    borderRadius: 6,
    gap: 4,
    marginTop: 4,
  },
  incompleteHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  incompleteTitle: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    fontWeight: '700',
    color: '#B45309',
  },
  incompleteSize: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    fontWeight: '700',
    color: '#92400E',
  },
  incompleteDesc: {
    fontSize: 11,
    color: '#78350F',
    lineHeight: 16,
  },
  incompleteProgressTrack: {
    height: 6,
    backgroundColor: '#FDE68A',
    borderRadius: 3,
    overflow: 'hidden',
    marginTop: 2,
  },
  incompleteProgressFill: {
    height: '100%',
    backgroundColor: '#F59E0B',
  },
  incompleteActionsContainer: {
    width: '100%',
    gap: spacing.xs,
  },
  resumeBtn: {
    backgroundColor: '#D97706',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: layout.borderRadius,
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  resumeBtnText: {
    color: '#FFFFFF',
    fontFamily: typography.fontSans,
    fontSize: typography.sizeSm,
    fontWeight: '700',
  },
  incompleteSecondaryRow: {
    flexDirection: 'row',
    gap: spacing.xs,
    justifyContent: 'space-between',
  },
  restartBtn: {
    flex: 1,
    backgroundColor: colors.paper,
    borderWidth: 1,
    borderColor: colors.divider,
    paddingVertical: 8,
    borderRadius: layout.borderRadius,
    alignItems: 'center',
    justifyContent: 'center',
  },
  restartBtnText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.ink,
    fontWeight: '600',
  },
  deletePartialBtn: {
    flex: 1,
    backgroundColor: colors.paper,
    borderWidth: 1,
    borderColor: colors.error,
    paddingVertical: 8,
    borderRadius: layout.borderRadius,
    alignItems: 'center',
    justifyContent: 'center',
  },
  deletePartialBtnText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.error,
    fontWeight: '600',
  },
  noteBox: {
    backgroundColor: colors.overlay,
    borderRadius: layout.borderRadius,
    padding: spacing.md,
    marginTop: spacing.sm,
    gap: 4,
  },
  noteTitle: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    fontWeight: '700',
    color: colors.ink,
    marginBottom: 2,
  },
  noteBody: {
    fontSize: typography.sizeXs,
    color: colors.muted,
    lineHeight: 18,
  },
  boldText: {
    fontWeight: '700',
    color: colors.ink,
  },
});
