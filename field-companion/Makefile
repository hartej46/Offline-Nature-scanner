# Field Companion — Makefile
# Checkpoint 3.1 & 3.2: One-command runners, builds, and offline test harnesses

.PHONY: help run test test-verbose build mobile-check mobile mobile-apk docker-build verify-all clean

help:
	@echo "🌱 Field Companion Commands:"
	@echo "  make run          - Start Ollama, FastAPI backend, and React webapp in one command"
	@echo "  make test         - Run 126 automated backend unit and integration tests"
	@echo "  make build        - Compile production bundle for React webapp"
	@echo "  make mobile-check - Type-check React Native mobile codebase"
	@echo "  make mobile       - Start Expo Go development server for LAN mobile access"
	@echo "  make mobile-apk   - Build standalone Android APK with Expo EAS"
	@echo "  make docker-build - Build Docker image for Render deployment verification"
	@echo "  make verify-all   - Run full verification (tests + web build + mobile check)"
	@echo "  make clean        - Remove Python and Node build artifacts and caches"

run:
	@chmod +x run.sh
	@./run.sh

test:
	@cd backend && python3 -m pytest tests/ -q

test-verbose:
	@cd backend && python3 -m pytest tests/ -v

build:
	@cd webapp && npm run build

mobile-check:
	@cd mobile && npx tsc --noEmit

mobile:
	@cd mobile && npx expo start --go

mobile-apk:
	@cd mobile && npx eas build -p android --profile preview

docker-build:
	@cd backend && docker build -t field-companion-backend:latest .

verify-all: test build mobile-check
	@echo "✓ All checks passed! Ready for Render deployment."

clean:
	@rm -rf backend/__pycache__ backend/app/__pycache__ backend/tests/__pycache__ backend/.pytest_cache
	@rm -rf webapp/dist
	@echo "✓ Cleaned cache and build artifacts."
