# 🛑 Shutdown Options for Distributed Email System

## Quick Reference

| Command | Speed | What's Removed | What's Preserved | Use Case |
|---------|-------|----------------|------------------|----------|
| `./stop.sh` | ⚡ Fastest | Containers only | Volumes, Images, Networks | Quick demo pause |
| `./stop-clean.sh` | 🔄 Fast | Containers + Volumes | Images, Networks | Clean restart |
| `./scripts/stop-demo.sh` | 🎛️ Interactive | User Choice (1-3 options) | Depends on choice | Full control |

## Detailed Options

### 1. Quick Stop (`./stop.sh`)
**Best for: Demo pauses, development**
```bash
./stop.sh
```
- ✅ Stops all containers
- ✅ Preserves all data (databases, uploaded files)
- ✅ Preserves Docker images (no rebuild needed)
- ✅ Fastest restart with `./start.sh`

### 2. Clean Stop (`./stop-clean.sh`)
**Best for: Fresh demo runs, clearing data**
```bash
./stop-clean.sh
```
- ✅ Stops all containers
- ❌ Removes volumes (clears databases, files)
- ✅ Preserves Docker images (no rebuild needed)
- ✅ Fast restart but with fresh data

### 3. Interactive Stop (`./scripts/stop-demo.sh`)
**Best for: Full control over cleanup**
```bash
./scripts/stop-demo.sh
```
Shows menu:
1. **Stop containers only** (same as `./stop.sh`)
2. **Stop + remove volumes** (same as `./stop-clean.sh`)
3. **Full cleanup** (removes everything including images)

## Restart After Each Option

| After... | Restart Command | Startup Time |
|----------|----------------|--------------|
| `./stop.sh` | `./start.sh` | ~30 seconds |
| `./stop-clean.sh` | `./start.sh` | ~60 seconds |
| Full cleanup | `./start.sh` | ~5-10 minutes |

## When to Use Each Option

### Quick Stop (`./stop.sh`)
- 👥 **Demo breaks/pauses**
- 🔄 **Development cycles**
- ⚡ **Need fastest restart**
- 💾 **Want to preserve demo data**

### Clean Stop (`./stop-clean.sh`) 
- 🆕 **Fresh demo for new audience**
- 🧹 **Clear previous demo data**
- 🔄 **Reset to clean state**
- ⚡ **Still want fast rebuild**

### Full Cleanup (`./scripts/stop-demo.sh` → option 3)
- 💽 **Free up disk space**
- 🏁 **Completely done with demo**
- 🛠️ **Troubleshooting issues**
- 🔄 **Major system changes**

## Emergency Stop
If containers are unresponsive:
```bash
docker-compose kill  # Force stop
docker-compose rm -f  # Remove containers
```