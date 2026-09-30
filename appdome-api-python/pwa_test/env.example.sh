# Copy to env.sh and fill in. env.sh and results/ are git-ignored.
# The wrapper reads these same variable names natively.

export APPDOME_API_KEY=""
# Leave empty. Every script passes --team_id explicitly so a stray value here can't redirect builds.
unset APPDOME_TEAM_ID

# Team used for the "team / no Short Flow" cases
export TEAM_ID_TEST=""

# PWA under test
export PWA_ADDRESS="https://example.com"
export PWA_APP_NAME="My PWA"

# Fusion Sets for builds that are NOT auto-built (team without Short Flow)
export FS_ANDROID_TEAM=""
export FS_IOS_TEAM=""

# Android Sign on Appdome
export ANDROID_KEYSTORE=""
export ANDROID_KEYSTORE_PASS=""
export ANDROID_KEYSTORE_ALIAS=""
export ANDROID_KEY_PASS=""

# iOS Sign on Appdome (the provisioning profile is also sent with the ipa PWA upload)
export IOS_P12=""
export IOS_P12_PASSWORD=""
export IOS_MOBILEPROVISION=""
