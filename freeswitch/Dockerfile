FROM debian:bookworm-slim

ARG FREESWITCH_VERSION=v1.10
ARG SOFIA_SIP_VERSION=v1.13.17
ARG DEBIAN_FRONTEND=noninteractive

# ── Install build + runtime dependencies ─────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential automake autoconf libtool pkg-config cmake git curl ca-certificates \
    libssl-dev libevent-dev libcurl4-openssl-dev libpcre3-dev libspeexdsp-dev \
    libedit-dev libsqlite3-dev libopus-dev libsndfile1-dev liblua5.2-dev \
    libavformat-dev libswscale-dev libjpeg-dev libpng-dev libtiff-dev \
    uuid-dev zlib1g-dev yasm \
    # Runtime deps (keep in single-stage build)
    sqlite3 libspeexdsp1 libopus0 libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ── Build spandsp (audio processing library) ─────────────────────────
WORKDIR /usr/src
RUN git clone --depth 1 https://github.com/freeswitch/spandsp.git \
    && cd spandsp \
    && ./bootstrap.sh \
    && ./configure --prefix=/usr \
    && make -j$(nproc) \
    && make install \
    && ldconfig

# ── Build sofia-sip (SIP stack) ──────────────────────────────────────
RUN git clone --depth 1 --branch ${SOFIA_SIP_VERSION} https://github.com/freeswitch/sofia-sip.git \
    && cd sofia-sip \
    && ./bootstrap.sh \
    && ./configure --prefix=/usr \
    && make -j$(nproc) \
    && make install \
    && ldconfig

# ── Build FreeSWITCH ─────────────────────────────────────────────────
RUN git clone --depth 1 --branch ${FREESWITCH_VERSION} https://github.com/signalwire/freeswitch.git
WORKDIR /usr/src/freeswitch

# Copy our minimal modules.conf to control which modules compile
COPY modules.conf modules.conf

RUN ./bootstrap.sh -j \
    && ./configure \
        --prefix=/usr \
        --sysconfdir=/etc \
        --localstatedir=/var \
        --disable-libks \
        --disable-signalwire \
    && make -j$(nproc) \
    && make install

# ── Build mod_audio_stream (WebSocket streaming module) ──────────────
WORKDIR /usr/src
RUN git clone --recurse-submodules https://github.com/amigniter/mod_audio_stream.git \
    && cd mod_audio_stream \
    && mkdir build && cd build \
    && cmake .. \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_BUILD_TYPE=Release \
    && make -j$(nproc) \
    && make install

# ── Overlay our config files on top of vanilla FreeSWITCH config ─────
COPY conf/autoload_configs/modules.conf.xml /etc/freeswitch/autoload_configs/modules.conf.xml
COPY conf/dialplan/inxphone.xml /etc/freeswitch/dialplan/inxphone.xml
COPY conf/sip_profiles/external/inxphone.xml /etc/freeswitch/sip_profiles/external/inxphone.xml

# ── Clean up build artifacts ─────────────────────────────────────────
RUN rm -rf /usr/src/spandsp /usr/src/sofia-sip /usr/src/freeswitch /usr/src/mod_audio_stream \
    && apt-get purge -y --auto-remove \
        build-essential automake autoconf libtool cmake git yasm \
    && rm -rf /var/lib/apt/lists/*

# ── Create freeswitch user and fix permissions ───────────────────────
RUN groupadd -r freeswitch && useradd -r -g freeswitch freeswitch \
    && chown -R freeswitch:freeswitch /etc/freeswitch \
    && mkdir -p /var/lib/freeswitch /var/log/freeswitch /var/run/freeswitch \
    && chown -R freeswitch:freeswitch /var/lib/freeswitch /var/log/freeswitch /var/run/freeswitch

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# SIP and RTP ports
EXPOSE 5060/tcp 5060/udp 16384-32768/udp

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD fs_cli -x "status" | grep -q "UP" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
