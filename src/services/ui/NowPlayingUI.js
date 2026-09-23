/**
 * NowPlayingUI — Tạo Embed "Now Playing" với thanh tiến trình & nút bấm tương tác.
 */

const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const { formatDuration, createProgressBar } = require('../../utils/formatters');

/** Màu sắc embed theo trạng thái */
const COLORS = {
    playing: 0x5865F2,   // Discord Blurple
    paused:  0xFEE75C,   // Vàng
    stopped: 0xED4245    // Đỏ
};

/** Biểu tượng repeat mode */
const REPEAT_ICONS = {
    off:   '➡️',
    track: '🔂',
    queue: '🔁'
};

/** Biểu tượng repeat mode cho nút bấm */
const REPEAT_LABELS = {
    off:   '🔁 Tắt',
    track: '🔂 Bài',
    queue: '🔁 DS'
};

class NowPlayingUI {
    /**
     * Tạo embed Now Playing và action row buttons.
     * @param {object} player - Kazagumo player
     * @param {object} track - Track đang phát
     * @param {import('../player/PlayerState').PlayerState} state - PlayerState
     * @returns {{ embed: EmbedBuilder, components: ActionRowBuilder[] }}
     */
    static create(player, track, state) {
        if (!track) {
            return {
                embed: new EmbedBuilder()
                    .setColor(COLORS.stopped)
                    .setTitle('🔇 Không có bài nào đang phát')
                    .setTimestamp(),
                components: []
            };
        }

        const isPaused = player.paused;
        const position = player.position || 0;
        const duration = track.length || track.duration || 0;
        const isStream = track.isStream || false;

        // --- Xây dựng Embed ---
        const embed = new EmbedBuilder()
            .setColor(isPaused ? COLORS.paused : COLORS.playing)
            .setAuthor({
                name: isPaused ? '⏸️ Đã tạm dừng' : '🎵 Đang phát',
                iconURL: 'https://cdn.discordapp.com/emojis/741605543046807626.gif'
            })
            .setTitle(track.title || 'Unknown')
            .setURL(track.uri || null)
            .setTimestamp();

        // Thumbnail
        if (track.thumbnail) {
            embed.setThumbnail(track.thumbnail);
        }

        // Nghệ sĩ
        if (track.author) {
            embed.addFields({ name: '🎤 Nghệ sĩ', value: track.author, inline: true });
        }

        // Người yêu cầu
        const requester = track.requester;
        if (requester) {
            const name = requester.globalName || requester.username || 'Unknown';
            embed.addFields({ name: '👤 Yêu cầu bởi', value: name, inline: true });
        }

        // Trạng thái (Repeat + Volume)
        const repeatIcon = REPEAT_ICONS[state.repeatMode] || '➡️';
        const repeatLabel = state.repeatMode === 'off' ? 'Tắt' : state.repeatMode === 'track' ? 'Lặp bài' : 'Lặp DS';
        const statusParts = [
            `${repeatIcon} ${repeatLabel}`,
            `🔊 ${player.volume || 100}%`
        ];
        embed.addFields({ name: '⚙️ Trạng thái', value: statusParts.join(' │ '), inline: false });

        // Thanh tiến trình
        const progressStr = isStream
            ? '🔴 LIVE'
            : createProgressBar(position, duration);
        embed.addFields({ name: '\u200b', value: `\`\`\`${progressStr}\`\`\``, inline: false });

        // Bài kế tiếp
        if (player.queue.length > 0) {
            const nextTrack = player.queue[0];
            const nextTitle = nextTrack.title || 'Unknown';
            const nextDur = formatDuration(nextTrack.length || nextTrack.duration || 0);
            embed.setFooter({
                text: `⏭ Kế tiếp: ${nextTitle} [${nextDur}] │ 📜 ${player.queue.length} bài trong hàng đợi`
            });
        } else {
            embed.setFooter({ text: '📭 Hàng đợi trống' });
        }

        // Avatar người yêu cầu (nếu có)
        if (requester && typeof requester.displayAvatarURL === 'function') {
            embed.setFooter({
                text: embed.data.footer?.text || '',
                iconURL: requester.displayAvatarURL({ size: 32 })
            });
        }

        // --- Xây dựng Buttons ---
        const row1 = new ActionRowBuilder().addComponents(
            new ButtonBuilder()
                .setCustomId('np_previous')
                .setEmoji('⏮')
                .setStyle(ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId('np_pause_resume')
                .setEmoji(isPaused ? '▶️' : '⏸️')
                .setStyle(isPaused ? ButtonStyle.Success : ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId('np_skip')
                .setEmoji('⏭')
                .setStyle(ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId('np_repeat')
                .setLabel(REPEAT_LABELS[state.repeatMode] || '🔁 Tắt')
                .setStyle(state.repeatMode !== 'off' ? ButtonStyle.Primary : ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId('np_shuffle')
                .setEmoji('🔀')
                .setStyle(ButtonStyle.Secondary)
        );

        const row2 = new ActionRowBuilder().addComponents(
            new ButtonBuilder()
                .setCustomId('np_vol_down')
                .setEmoji('🔉')
                .setStyle(ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId('np_vol_up')
                .setEmoji('🔊')
                .setStyle(ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId('np_queue')
                .setLabel('📜 Hàng đợi')
                .setStyle(ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId('np_stop')
                .setLabel('🛑 Dừng')
                .setStyle(ButtonStyle.Danger)
        );

        return {
            embed,
            components: [row1, row2]
        };
    }
}

module.exports = NowPlayingUI;
