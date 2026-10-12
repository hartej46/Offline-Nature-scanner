import React, { useState, useEffect } from 'react';
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
import { getStatus, setApiBaseUrl, getApiBaseUrl } from '../services/api';
import type { StatusResponse } from '../services/api';
import ModelPackModal from '../components/ModelPackModal';

interface SettingsScreenProps {
  onBack: () => void;
}

export default function SettingsScreen({ onBack }: SettingsScreenProps) {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [serverUrl, setServerUrl] = useState(getApiBaseUrl());
  const [showModelPackModal, setShowModelPackModal] = useState(false);

  const [deviceModelStatus, setDeviceModelStatus] = useState<{
    installed: boolean;
    incomplete: boolean;
    name: string;
    sizeFormatted: string;
    details: string;
  }>({
    installed: false,
    incomplete: false,
    name: 'None',
    sizeFormatted: '0 MB',
    details: 'No model installed on device',
  });

  const checkDeviceStorage = async () => {
    try {
      const FileSystem = await import('expo-file-system/legacy');
      const baseDir = FileSystem.documentDirectory || '';
      const e2bInfo = await FileSystem.getInfoAsync(`${baseDir}models/gemma4-e2b.gguf`);
      const e4bInfo = await FileSystem.getInfoAsync(`${baseDir}models/gemma4-e4b.gguf`);

      const e2bBytes = e2bInfo.exists ? (e2bInfo as any).size || 0 : 0;
      const e4bBytes = e4bInfo.exists ? (e4bInfo as any).size || 0 : 0;

      if (e4bBytes >= 9000000000) {
        setDeviceModelStatus({
          installed: true,
          incomplete: false,
          name: 'Google Gemma 4 E4B',
          sizeFormatted: `${(e4bBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`,
          details: 'Verified on device • Offline ready',
        });
      } else if (e2bBytes >= 2000000000) {
        setDeviceModelStatus({
          installed: true,
          incomplete: false,
          name: 'Google Gemma 4 E2B',
          sizeFormatted: `${(e2bBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`,
          details: 'Verified on device • Offline ready',
        });
      } else if (e4bBytes > 0) {
        setDeviceModelStatus({
          installed: false,
          incomplete: true,
          name: 'Google Gemma 4 E4B',
          sizeFormatted: `${(e4bBytes / (1024 * 1024)).toFixed(1)} MB`,
          details: `Incomplete (${Math.round((e4bBytes / 9608338848) * 100)}%) • Cannot run on device`,
        });
      } else if (e2bBytes > 0) {
        setDeviceModelStatus({
          installed: false,
          incomplete: true,
          name: 'Google Gemma 4 E2B',
          sizeFormatted: `${(e2bBytes / (1024 * 1024)).toFixed(1)} MB`,
          details: `Incomplete (${Math.round((e2bBytes / 2019377376) * 100)}%) • Cannot run on device`,
        });
      } else {
        setDeviceModelStatus({
          installed: false,
          incomplete: false,
          name: 'None installed',
          sizeFormatted: '0 MB',
          details: 'No model stored on device',
        });
      }
    } catch {
      // Ignore
    }
  };

  useEffect(() => {
    checkDeviceStorage();
    getStatus()
      .then(setStatus)
      .catch((e) => console.log('Status query failed', e));
  }, []);

  const handleSaveUrl = () => {
    setApiBaseUrl(serverUrl);
    checkDeviceStorage();
    getStatus()
      .then(setStatus)
      .catch((e) => console.log('Status query failed', e));
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Text style={styles.backBtnText}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Settings</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* Backend Server Configuration */}
        <View style={styles.section}>
          <Text style={styles.metaLabel}>BACKEND CONNECTION</Text>
          <Text style={styles.descText}>
            IP of Mac running the local FastAPI server on WiFi / hotspot:
          </Text>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              value={serverUrl}
              onChangeText={setServerUrl}
              placeholder="http://192.168.1.x:8000"
              placeholderTextColor={colors.muted}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <TouchableOpacity style={styles.saveBtn} onPress={handleSaveUrl}>
              <Text style={styles.saveBtnText}>Connect</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Offline Model Status */}
        <View style={styles.section}>
          <Text style={styles.metaLabel}>ON-DEVICE HARDWARE STORAGE</Text>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Device Model</Text>
            <Text style={styles.rowValueMono}>
              {deviceModelStatus.name}
            </Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Phone Storage Used</Text>
            <Text style={styles.rowValue}>
              {deviceModelStatus.sizeFormatted}
            </Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Checklist species</Text>
            <Text style={styles.rowValue}>
              {status ? `${status.species_count} species loaded` : 'Connecting to server...'}
            </Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Offline Status</Text>
            <View style={styles.statusIndicator}>
              <View
                style={[
                  styles.statusDot,
                  deviceModelStatus.incomplete && { backgroundColor: '#F59E0B' },
                  !deviceModelStatus.installed &&
                    !deviceModelStatus.incomplete && { backgroundColor: '#9CA3AF' },
                ]}
              />
              <Text
                style={[
                  styles.rowValue,
                  deviceModelStatus.incomplete && { color: '#B45309' },
                  !deviceModelStatus.installed &&
                    !deviceModelStatus.incomplete && { color: '#6B7280' },
                ]}
              >
                {deviceModelStatus.installed
                  ? 'Verified on Device'
                  : deviceModelStatus.incomplete
                  ? 'Incomplete Download'
                  : 'Not Installed on Device'}
              </Text>
            </View>
          </View>

          {/* Gemma Model Pack Button */}
          <TouchableOpacity
            style={styles.packManagerBtn}
            onPress={() => setShowModelPackModal(true)}
            activeOpacity={0.8}
          >
            <View style={styles.packManagerLeft}>
              <Text style={styles.packManagerIcon}>
                {deviceModelStatus.incomplete ? '⚠️' : '📦'}
              </Text>
              <View>
                <Text style={styles.packManagerTitle}>
                  {deviceModelStatus.installed
                    ? deviceModelStatus.name
                    : deviceModelStatus.incomplete
                    ? `${deviceModelStatus.name} (Incomplete)`
                    : 'Download On-Device Model'}
                </Text>
                <Text style={styles.packManagerSub}>
                  {deviceModelStatus.details}
                </Text>
              </View>
            </View>
            <Text style={styles.packManagerArrow}>
              {deviceModelStatus.incomplete
                ? 'Resume ›'
                : deviceModelStatus.installed
                ? 'Manage ›'
                : 'Download ›'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Privacy Note */}
        <View style={styles.section}>
          <Text style={styles.metaLabel}>PRIVACY</Text>
          <View style={styles.privacyCard}>
            <Text style={styles.privacyText}>
              Everything stays on this phone and local device. No data is sent to
              any external cloud service.
            </Text>
          </View>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Field Companion • Mobile React Native
          </Text>
        </View>
      </ScrollView>

      <ModelPackModal
        visible={showModelPackModal}
        onClose={() => setShowModelPackModal(false)}
      />
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
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeLg,
    color: colors.ink,
    fontWeight: '600',
  },
  content: {
    padding: spacing.lg,
    gap: spacing.xl,
  },
  section: {
    gap: spacing.sm,
  },
  metaLabel: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
    letterSpacing: 0.5,
  },
  descText: {
    fontSize: typography.sizeSm,
    color: colors.ink,
    marginBottom: spacing.xs,
  },
  inputRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  input: {
    flex: 1,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.overlay,
    borderRadius: layout.borderRadius,
    padding: spacing.sm,
    fontSize: typography.sizeSm,
    fontFamily: typography.fontMono,
    color: colors.ink,
  },
  saveBtn: {
    backgroundColor: colors.moss,
    paddingHorizontal: spacing.md,
    justifyContent: 'center',
    borderRadius: layout.borderRadius,
  },
  saveBtnText: {
    color: colors.paper,
    fontSize: typography.sizeSm,
    fontWeight: '600',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: layout.hairlineWidth,
    borderBottomColor: colors.divider,
    alignItems: 'center',
  },
  rowLabel: {
    fontSize: typography.sizeSm,
    color: colors.ink,
  },
  rowValue: {
    fontSize: typography.sizeSm,
    color: colors.muted,
  },
  rowValueMono: {
    fontSize: typography.sizeXs,
    color: colors.muted,
    fontFamily: typography.fontMono,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.moss,
    marginRight: 6,
  },
  privacyCard: {
    backgroundColor: colors.overlay,
    padding: spacing.md,
    borderRadius: layout.borderRadius,
    borderWidth: layout.hairlineWidth,
    borderColor: colors.divider,
  },
  privacyText: {
    fontSize: typography.sizeSm,
    color: colors.ink,
    lineHeight: 20,
  },
  footer: {
    alignItems: 'center',
    marginTop: spacing.lg,
  },
  footerText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
  packManagerBtn: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(79, 107, 58, 0.08)',
    borderWidth: layout.hairlineWidth,
    borderColor: 'rgba(79, 107, 58, 0.3)',
    borderRadius: layout.borderRadius,
    padding: spacing.md,
    marginTop: spacing.xs,
  },
  packManagerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  packManagerIcon: {
    fontSize: typography.sizeLg,
  },
  packManagerTitle: {
    fontSize: typography.sizeSm,
    fontWeight: '600',
    color: colors.ink,
  },
  packManagerSub: {
    fontSize: typography.sizeXs,
    color: colors.muted,
    fontFamily: typography.fontMono,
    marginTop: 2,
  },
  packManagerArrow: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeSm,
    color: colors.moss,
    fontWeight: '600',
  },
});
