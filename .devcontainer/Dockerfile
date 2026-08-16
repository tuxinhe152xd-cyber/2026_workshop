# RNA-seq × Agent 工作坊 —— Codespaces 用 image
#
# 由講師 build 一次、推到 GHCR，學員的 Codespace 直接拉，不在課堂上做 conda solve。
#
#   docker build -f .devcontainer/Dockerfile -t ghcr.io/<帳號>/rnaseq-agent:1.0 .devcontainer
#   docker push ghcr.io/<帳號>/rnaseq-agent:1.0
#
# ── channel 順序不要動 ────────────────────────────────────────────────────
# `conda config --add` 是「插到最前面」，所以下面三行跑完的優先序是
#   conda-forge > bioconda > defaults
# 這三個**都要有**。只用 conda-forge + bioconda 會解不開：
# 實測時 solver 跑了 341 秒後失敗，一路退化到 pydeseq2 0.3.3 撞上 anndata==0.8.0。
# 補上 defaults 之後，同一份清單 23 秒就解完。
#
# 註：Anaconda 的 defaults channel 在大型組織有授權條款要注意。
#     學術教學用途一般沒問題，但把 image 推成 public 之前值得確認一次。
# 用 miniforge3 而不是 continuumio/miniconda3 —— 後者官方已標示停止維護。
# 實測兩者在下面這份清單上都是 25 秒解完，結果相同。
FROM condaforge/miniforge3:latest

ENV DEBIAN_FRONTEND=noninteractive

# devcontainer 需要 git；opencode 需要 curl / ca-certificates / unzip
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl git ca-certificates unzip procps less vim nano sudo \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 只裝這場工作坊真的會用到的東西。
# hisat2 / STAR / subread / samtools / fastp / jupyter 都拿掉了。
#
# ⚠ openjdk 必須明確釘住，不能讓 solver 自己挑。
# 不釘的話它會選到 openjdk 11.0.1（2018 年版），那顆的 JIT 有 bug：
# trimmomatic 跑到比較大的樣本時會在 C2 編譯後的
# IlluminaClippingTrimmer.readsSeqCompare 上 SIGILL 當掉。
# 症狀很陰險 —— 前幾個樣本正常，最大的那個才炸，而且不是每次都炸。
# 原本 8.5 GB 那顆 image 之所以沒事，是因為完整套件清單剛好把 JDK 拉到 17。
RUN conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda create -y -n rnaseq-demo python=3.12.3 \
        fastqc \
        multiqc \
        trimmomatic \
        kallisto=0.48.0 \
        pydeseq2 \
        matplotlib \
        "openjdk>=17" && \
    conda clean -afy && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate rnaseq-demo" >> ~/.bashrc

# 把 conda env 放進全域 PATH。
# 只在 ~/.bashrc 裡 conda activate 的話，那只對「互動式」shell 生效；
# agent 執行指令走的是非互動的 `bash -c`，PATH 裡不會有 kallisto，
# 學員會看到 `kallisto: command not found` 而完全不知道為什麼。
# 這是整個 image 最關鍵的一行。
ENV PATH=/opt/conda/envs/rnaseq-demo/bin:/opt/conda/bin:$PATH

# skill 裡寫的是不帶版本號的 adapter 路徑，補一個 symlink 確保它一定存在
RUN set -e; \
    if [ ! -e /opt/conda/envs/rnaseq-demo/share/trimmomatic ]; then \
        d=$(ls -d /opt/conda/envs/rnaseq-demo/share/trimmomatic-* | head -1); \
        ln -s "$d" /opt/conda/envs/rnaseq-demo/share/trimmomatic; \
    fi; \
    ls /opt/conda/envs/rnaseq-demo/share/trimmomatic/adapters/TruSeq3-PE-2.fa

ARG OPENCODE_VERSION=1.18.16
RUN curl -fsSL https://opencode.ai/install | VERSION=${OPENCODE_VERSION} bash \
    && /root/.opencode/bin/opencode --version
ENV PATH=/root/.opencode/bin:$PATH

COPY opencode.json /root/.config/opencode/opencode.json

ENV TERM=xterm-256color

# build 完自我檢查，錯了在這裡就爆，不要等到課堂上
RUN kallisto version && \
    fastqc --version && \
    multiqc --version && \
    trimmomatic -version && \
    opencode --version && \
    python -c "import pydeseq2, pandas, numpy, matplotlib; print('pydeseq2', pydeseq2.__version__)"
