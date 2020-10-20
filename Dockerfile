ARG GO_VERSION="1.14.4"
ARG SINGULARITY_VERSION="3.5.3"

# Build Singularity.
FROM golang:${GO_VERSION}-buster as builder

# Necessary to pass the arg from outside this build (it is defined before the FROM).
ARG SINGULARITY_VERSION

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        cryptsetup \
        libssl-dev \
        uuid-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/hpcng/singularity/releases/download/v${SINGULARITY_VERSION}/singularity-${SINGULARITY_VERSION}.tar.gz" \
    | tar -xz \
    && cd singularity \
    && ./mconfig -p /usr/local/singularity \
    && cd builddir \
    && make \
    && make install


# Create final image.
# Based on this wonderful work https://github.com/fcwu/docker-ubuntu-vnc-desktop
FROM dorowu/ubuntu-desktop-lxde-vnc:focal

# Install singularity into the final image.
COPY --from=builder /usr/local/singularity /usr/local/singularity


# Install singularity's and lmod's runtime dependencies.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        cryptsetup \
        squashfs-tools \
        lua-bit32 \
        lua-filesystem \
        lua-json \
        lua-lpeg \
        lua-posix \
        lua-term \
        lua5.2 \
        lmod \
        git \
    && rm -rf /var/lib/apt/lists/*

# add module script
COPY ./config/module.sh /usr/share/

# Add Visual Studio code
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
RUN mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
RUN echo "deb [arch=amd64] http://packages.microsoft.com/repos/vscode stable main" | tee /etc/apt/sources.list.d/vs-code.list

# Install useful packages:
RUN apt-get update \
    && apt-get install -y \
        code \
        emacs \
        fish \
        git-annex \
        gimp \
        htop \
        imagemagick \
        less \
        nano \
        openssh-client \
        python3-pip \
        rclone \
        rsync \
        tree \
        vim \
    && rm -rf /var/lib/apt/lists/*

# cleanup vs-code.list file to avoid apt error:
RUN rm /etc/apt/sources.list.d/vs-code.list

# install datalad
RUN pip3 install datalad datalad_container \
    && rm -rf /root/.cache/pip \
    && rm -rf /home/ubuntu/.cache/

# setup module system & singularity
COPY ./config/.bashrc /root/.bashrc


# Install nipype: 
RUN apt-get update \
    && apt-get install -y \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install nipype \
    && rm -rf /root/.cache/pip \
    && rm -rf /home/ubuntu/.cache/

# Install julia:
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libzstd1 \
        julia \
        libjulia1 \
        libgfortran5 \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*


# Necessary to pass the args from outside this build (it is defined before the FROM).
ARG GO_VERSION
ARG SINGULARITY_VERSION

ENV PATH="/usr/local/singularity/bin:${PATH}" \
    GO_VERSION=${GO_VERSION} \
    SINGULARITY_VERSION=${SINGULARITY_VERSION} \
    MODULEPATH=/opt/vnm

# configure tiling of windows SHIFT-ALT-CTR-{Left,right,top,Bottom} and other openbox desktop mods
COPY ./config/rc.xml /etc/xdg/openbox

# configure ITKsnap
COPY ./config/.itksnap.org /root/.itksnap.org
COPY ./config/mimeapps.list /root/.config/mimeapps.list

# Use custom bottom panel configuration
COPY ./config/panel /root/.config/lxpanel/LXDE/panels/panel


# Application and submenu icons
WORKDIR /
RUN git clone https://github.com/NeuroDesk/neurodesk.git /neurodesk
WORKDIR /neurodesk
# RUN bash neurodesk.sh --lxde_system_install true
RUN bash build.sh --lxde
RUN bash install.sh

RUN mkdir -p /root/Desktop/
RUN ln -s /vnm /root/Desktop/vnm