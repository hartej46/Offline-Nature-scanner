import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing, typography, layout } from '../styles/theme';
import { getJournal } from '../services/api';
import type { JournalEntry } from '../services/api';

interface JournalScreenProps {
  onSelectEntry: (entry: JournalEntry) => void;
  onBack: () => void;
}

export default function JournalScreen({
  onSelectEntry,
  onBack,
}: JournalScreenProps) {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  const fetchEntries = async (search?: string) => {
    try {
      setLoading(true);
      const res = await getJournal(search);
      setEntries(res.observations || []);
    } catch (err) {
      console.error('Failed to load journal', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, []);

  const renderItem = ({ item }: { item: JournalEntry }) => (
    <TouchableOpacity
      style={styles.entryItem}
      onPress={() => onSelectEntry(item)}
      activeOpacity={0.7}
    >
      <View style={styles.entryHeader}>
        <Text style={styles.entrySpecies}>
          {item.common_name || 'Unidentified'}
        </Text>
        <Text style={styles.entryDate}>
          {new Date(item.ts).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
          })}
        </Text>
      </View>
      {item.sci_name ? (
        <Text style={styles.entrySci}>{item.sci_name}</Text>
      ) : null}
      {item.notes ? (
        <Text style={styles.entryNotes} numberOfLines={2}>
          {item.notes}
        </Text>
      ) : null}
      <View style={styles.entryFooter}>
        {item.source ? (
          <View style={styles.sourceTag}>
            <Text style={styles.sourceTagText}>{item.source.toUpperCase()}</Text>
          </View>
        ) : null}
        {item.confidence !== undefined && item.confidence !== null ? (
          <Text style={styles.confidenceText}>
            {Math.round(item.confidence * 100)}% conf
          </Text>
        ) : null}
      </View>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Text style={styles.backBtnText}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Trail Journal</Text>
      </View>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search by species, notes..."
          placeholderTextColor={colors.muted}
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={() => fetchEntries(query)}
          returnKeyType="search"
        />
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.moss} size="small" />
        </View>
      ) : entries.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyTitle}>No sightings yet</Text>
          <Text style={styles.emptyText}>
            Step outside and listen or photograph to start your journal.
          </Text>
        </View>
      ) : (
        <FlatList
          data={entries}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.listContent}
        />
      )}
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
  searchContainer: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  searchInput: {
    borderWidth: layout.hairlineWidth,
    borderColor: colors.divider,
    backgroundColor: colors.overlay,
    borderRadius: layout.borderRadius,
    padding: spacing.md,
    fontSize: typography.sizeBase,
    color: colors.ink,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
  },
  emptyTitle: {
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeXl,
    color: colors.ink,
    marginBottom: spacing.xs,
  },
  emptyText: {
    fontSize: typography.sizeSm,
    color: colors.muted,
    textAlign: 'center',
    lineHeight: 20,
  },
  listContent: {
    paddingHorizontal: spacing.lg,
  },
  entryItem: {
    paddingVertical: spacing.md,
    borderBottomWidth: layout.hairlineWidth,
    borderBottomColor: colors.divider,
    gap: spacing.xs,
  },
  entryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  entrySpecies: {
    fontFamily: typography.fontSerif,
    fontSize: typography.sizeBase,
    fontWeight: '600',
    color: colors.ink,
  },
  entryDate: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
  entrySci: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
    fontStyle: 'italic',
  },
  entryNotes: {
    fontSize: typography.sizeSm,
    color: colors.ink,
  },
  entryFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  sourceTag: {
    backgroundColor: colors.overlay,
    paddingHorizontal: spacing.xs,
    paddingVertical: 2,
    borderRadius: layout.borderRadius,
  },
  sourceTagText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
  confidenceText: {
    fontFamily: typography.fontMono,
    fontSize: typography.sizeXs,
    color: colors.muted,
  },
});
