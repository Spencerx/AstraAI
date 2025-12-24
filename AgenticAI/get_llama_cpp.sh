git clone https://github.com/nataraj2/llama.cpp.git
cd llama.cpp
mkdir -p build
cmake -B build -DLLAMA_CUDA=ON
cmake --build build -j
