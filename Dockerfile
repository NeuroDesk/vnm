ARG GO_VERSION="1.14.4"
ARG SINGULARITY_VERSION="3.5.3"
ARG LINUX_USER_NAME="neuro"

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


# Add Visual Studio code
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
RUN mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
RUN echo "deb [arch=amd64] http://packages.microsoft.com/repos/vscode stable main" | tee /etc/apt/sources.list.d/vs-code.list

# Install packages: code, vim, git-annex
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        htop \
        fish \
        vim \
        code \
        git-annex \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# cleanup vs-code.list file to avoid apt error:
RUN rm /etc/apt/sources.list.d/vs-code.list

# install datalad
RUN pip3 install datalad datalad_container

# setup module system & singularity
ARG LINUX_USER_NAME
RUN mkdir -p /home/${LINUX_USER_NAME}/
COPY ./scripts/.bashrc /home/${LINUX_USER_NAME}/.bashrc

# Necessary to pass the args from outside this build (it is defined before the FROM).
ARG GO_VERSION
ARG SINGULARITY_VERSION

ENV PATH="/usr/local/singularity/bin:${PATH}" \
    GO_VERSION=${GO_VERSION} \
    SINGULARITY_VERSION=${SINGULARITY_VERSION} \
    MODULEPATH=/opt/vnm

# configure tiling of windows SHIFT-ALT-CTR-{Left,right,top,Bottom} and other openbox desktop mods
COPY ./scripts/rc.xml /etc/xdg/openbox

# add custom scripts
COPY ./scripts/* /usr/share/

# Use custom bottom panel configuration
COPY ./menus/panel /home/${LINUX_USER_NAME}/.config/lxpanel/LXDE/panels/panel

# Application and submenu icons
RUN mkdir -p /home/${LINUX_USER_NAME}/.config/lxpanel/LXDE/icons
COPY ./menus/icons/* /home/${LINUX_USER_NAME}/.config/lxpanel/LXDE/icons/
# Adding the vnm logo for a default icon
COPY virtualneuromachine_logo_small.png /home/${LINUX_USER_NAME}/.config/lxpanel/LXDE/icons/vnm.png
RUN chmod 644 /home/${LINUX_USER_NAME}/.config/lxpanel/LXDE/icons/*

# Main-menu config. Add Menu changes to vnm-applications.menu
COPY ./menus/lxde-applications.menu /etc/xdg/menus/
COPY ./menus/vnm-applications.menu /etc/xdg/menus/

RUN chmod 644 /etc/xdg/menus/lxde-applications.menu

# Build the menu
WORKDIR /tmp
COPY ./menus/build_menu.py ./menus/apps.json /tmp/
RUN python3 build_menu.py

WORKDIR /vnm
