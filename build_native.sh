#!/usr/bin/env bash
# Build libassimp.so (v4.1.0, cocok dengan assimp.dll 2018 bawaan editor) dan
# libetcwrap.so (Etc2Comp = sumber etctool.exe) untuk Android arm64-v8a.
set -euo pipefail
OUT="${1:-$PWD/native-out}"; mkdir -p "$OUT"
NDK="${ANDROID_NDK_LATEST_HOME:-${ANDROID_NDK_HOME:?NDK tidak ditemukan}}"
TC="$NDK/build/cmake/android.toolchain.cmake"
W="$(mktemp -d)"; cd "$W"

git clone --depth 1 --branch v4.1.0 https://github.com/assimp/assimp.git
git clone --depth 1 https://github.com/google/etc2comp.git

cmake -S assimp -B assimp/b -DCMAKE_TOOLCHAIN_FILE="$TC" -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-24 -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
  -DASSIMP_BUILD_ASSIMP_TOOLS=OFF -DASSIMP_BUILD_TESTS=OFF -DASSIMP_BUILD_SAMPLES=OFF \
  -DASSIMP_NO_EXPORT=ON -DASSIMP_BUILD_ZLIB=ON \
  -DCMAKE_CXX_FLAGS="-Wno-error -Wno-deprecated-declarations" -DCMAKE_C_FLAGS="-Wno-error"
cmake --build assimp/b -j"$(nproc)"
cp "$(find assimp/b -name 'libassimp*.so' | head -1)" "$OUT/libassimp.so"

mkdir wrap
cat > wrap/wrap.cpp <<'CPP'
#include "Etc.h"
#include "EtcImage.h"
#include <vector>
extern "C" {
// fmt: 0=ETC1, 1=RGB8 (ETC2), 2=RGBA8 (ETC2 EAC)
int etc_encode(const unsigned char* rgba, unsigned w, unsigned h, int fmt, float effort,
               unsigned char** bits, unsigned* nbytes) {
  std::vector<float> px((size_t)w * h * 4);
  for (size_t i = 0; i < px.size(); ++i) px[i] = rgba[i] / 255.0f;
  Etc::Image::Format f = fmt == 0 ? Etc::Image::Format::ETC1
                       : fmt == 1 ? Etc::Image::Format::RGB8
                                  : Etc::Image::Format::RGBA8;
  unsigned ew = 0, eh = 0; int ms = 0;
  Etc::Encode(px.data(), w, h, f, Etc::ErrorMetric::RGBX, effort, 1, 1,
              bits, nbytes, &ew, &eh, &ms);
  return 1;
}
void etc_free(unsigned char* p) { delete[] p; }
}
CPP
cat > wrap/CMakeLists.txt <<CMK
cmake_minimum_required(VERSION 3.10)
project(etcwrap CXX)
set(CMAKE_CXX_STANDARD 14)
file(GLOB SRC "$W/etc2comp/EtcLib/Etc/*.cpp" "$W/etc2comp/EtcLib/EtcCodec/*.cpp" "wrap.cpp")
add_library(etcwrap SHARED \${SRC})
target_include_directories(etcwrap PRIVATE "$W/etc2comp/EtcLib/Etc" "$W/etc2comp/EtcLib/EtcCodec")
CMK
cmake -S wrap -B wrap/b -DCMAKE_TOOLCHAIN_FILE="$TC" -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-24 -DCMAKE_BUILD_TYPE=Release
cmake --build wrap/b -j"$(nproc)"
cp wrap/b/libetcwrap.so "$OUT/libetcwrap.so"
ls -la "$OUT"
