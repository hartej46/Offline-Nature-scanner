import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, StatusBar, LogBox } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import HomeScreen from './src/screens/HomeScreen';
import ListeningScreen from './src/screens/ListeningScreen';
import ResultScreen from './src/screens/ResultScreen';
import JournalScreen from './src/screens/JournalScreen';
import SpeciesDetailScreen from './src/screens/SpeciesDetailScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import { colors, spacing, typography, layout } from './src/styles/theme';
import type { IdentifyResponse, JournalEntry } from './src/services/api';

LogBox.ignoreLogs([
  'SafeAreaView has been deprecated',
  'Response.blob() is using React Native',
  'Response.blob()',
  'react-native-safe-area-context',
]);

type Tab = 'home' | 'journal' | 'settings';

export default function App() {
  const [currentTab, setCurrentTab] = useState<Tab>('home');
  const [isListening, setIsListening] = useState(false);
  const [currentResult, setCurrentResult] = useState<IdentifyResponse | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null);

  const handleStartListening = () => {
    setIsListening(true);
  };

  const handleStopListening = () => {
    setIsListening(false);
  };

  const handleShowResult = (result: IdentifyResponse) => {
    setIsListening(false);
    setCurrentResult(result);
  };

  const handleSaveToJournal = () => {
    setCurrentResult(null);
    setCurrentTab('journal');
  };

  return (
    <SafeAreaProvider>
      <View style={styles.appContainer}>

      <StatusBar barStyle="dark-content" backgroundColor={colors.paper} />

      {/* Screen Views */}
      <View style={styles.mainContent}>
        {selectedEntry ? (
          <SpeciesDetailScreen
            entry={selectedEntry}
            onBack={() => setSelectedEntry(null)}
          />
        ) : currentResult ? (
          <ResultScreen
            result={currentResult}
            onBack={() => setCurrentResult(null)}
            onSaveToJournal={handleSaveToJournal}
          />
        ) : isListening ? (
          <ListeningScreen
            onStop={handleStopListening}
            onShowResult={handleShowResult}
          />
        ) : currentTab === 'home' ? (
          <HomeScreen
            onStartListening={handleStartListening}
            onShowResult={handleShowResult}
            onNavigateJournal={() => setCurrentTab('journal')}
          />
        ) : currentTab === 'journal' ? (
          <JournalScreen
            onSelectEntry={(entry) => setSelectedEntry(entry)}
            onBack={() => setCurrentTab('home')}
          />
        ) : (
          <SettingsScreen onBack={() => setCurrentTab('home')} />
        )}
      </View>

      {/* Bottom Navigation Bar */}
      {!isListening && !currentResult && !selectedEntry && (
        <View style={styles.navBar}>
          <TouchableOpacity
            style={styles.navItem}
            onPress={() => setCurrentTab('home')}
          >
            <Text
              style={[
                styles.navText,
                currentTab === 'home' && styles.navTextActive,
              ]}
            >
              Companion
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.navItem}
            onPress={() => setCurrentTab('journal')}
          >
            <Text
              style={[
                styles.navText,
                currentTab === 'journal' && styles.navTextActive,
              ]}
            >
              Journal
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.navItem}
            onPress={() => setCurrentTab('settings')}
          >
            <Text
              style={[
                styles.navText,
                currentTab === 'settings' && styles.navTextActive,
              ]}
            >
              Settings
            </Text>
          </TouchableOpacity>
        </View>
      )}
      </View>
    </SafeAreaProvider>
  );
}


const styles = StyleSheet.create({
  appContainer: {
    flex: 1,
    backgroundColor: colors.paper,
  },
  mainContent: {
    flex: 1,
  },
  navBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: spacing.md,
    borderTopWidth: layout.hairlineWidth,
    borderTopColor: colors.divider,
    backgroundColor: colors.paper,
  },
  navItem: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    minHeight: layout.tapTarget,
    justifyContent: 'center',
    alignItems: 'center',
  },
  navText: {
    fontFamily: typography.fontSans,
    fontSize: typography.sizeSm,
    color: colors.muted,
  },
  navTextActive: {
    color: colors.moss,
    fontWeight: '600',
  },
});
