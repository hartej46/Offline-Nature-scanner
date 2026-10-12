import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing, typography, layout } from '../styles/theme';
import type { JournalEntry } from '../services/api';

interface SpeciesDetailScreenProps {
  entry: JournalEntry;
  onBack: () => void;
}

export default function SpeciesDetailScreen({
  entry,
  onBack,
}: SpeciesDetailScreenProps) {
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Text style={styles.backBtnText}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Observation #{entry.id}</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.titleSection}>
          <Text style={styles.speciesName}>{entry.common_name || 'Observation'}</Text>
          {entry.sci_name ? (
            <Text style={styles.sciName}>{entry.sci_name}</Text>
          ) : null}
        </View>

        <View style={styles.section}>
          <Text style={styles.metaLabel}>DETAILS</Text>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Recorded</Text>
            <Text style={styles.rowValue}>
              {new Date(entry.ts).toLocaleString()}
            </Text>
          </View>
          {entry.source ? (
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Source</Text>
              <Text style={styles.rowValue}>{entry.source.toUpperCase()}</Text>
            </View>
          ) : null}
          {entry.confidence !== undefined && entry.confidence !== null ? (
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Confidence</Text>
              <Text style={styles.rowValue}>
                {Math.round(entry.confidence * 100)}%
              </Text>
            </View>
          ) : null}
          {entry.lat !== undefined && entry.lat !== null ? (
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Coordinates</Text>
              <Text style={styles.rowValue}>
                {entry.lat.toFixed(4)}, {entry.lon?.toFixed(4)}
              </Text>
            </View>
          ) : null}
        </View>

        {entry.notes ? (
          <View style={styles.section}>
            <Text style={styles.metaLabel}>USER NOTES</Text>
            <View style={styles.card}>
              <Text style={styles.cardText}>{entry.notes}</Text>
            </View>
          </View>
        ) : null}

        {entry.response ? (
          <View style={styles.section}>
            <Text style={styles.metaLabel}>ANALYSIS & CONFIRMATION</Text>
            <View style={styles.card}>
              <Text style={styles.cardText}>{entry.response}</Text>
            </View>
          </View>
        ) : null}
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
  },
  content: {
    padding: spacing.lg,
    gap: spacing.xl,
  },
  titleSection: {
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
  section: {
    gap: spacing.xs,
  },
  metaLabel: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
    letterSpacing: 0.5,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: layout.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  rowLabel: {
    fontSize: typography.sizeSm,
    color: colors.ink,
  },
  rowValue: {
    fontSize: typography.sizeSm,
    color: colors.muted,
    fontFamily: typography.fontMono,
  },
  card: {
    backgroundColor: colors.overlay,
    padding: spacing.md,
    borderRadius: layout.borderRadius,
    marginTop: spacing.xs,
  },
  cardText: {
    fontSize: typography.sizeSm,
    lineHeight: 20,
    color: colors.ink,
  },
});
