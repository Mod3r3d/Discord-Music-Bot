/**
 * /history — Xem lịch sử các bài hát đã phát.
 */

const { EmbedBuilder } = require('discord.js');
const { getState } = require('../services/player/PlayerState');
const { formatDuration, truncate } = require('../utils/formatters');

const definition = {
    name: 'history',
    description: 'Xem lịch sử các bài hát đã phát gần đây'
};

async function execute(interaction, _playerService) {
    const state = getState(interaction.guild.id);

    if (state.history.length === 0) {
        return interaction.reply({ content: '📭 Lịch sử trống, chưa có bài nào được phát.', ephemeral: true });
    }

    // Hiển thị tối đa 15 bài gần nhất
    const maxDisplay = Math.min(15, state.history.length);
    const lines = [];

    for (let i = 0; i < maxDisplay; i++) {
        const track = state.history[i];
        const num = String(i + 1).padStart(2, '0');
        const dur = formatDuration(track.duration || 0);
        const title = truncate(track.title || 'Unknown', 45);
        const requester = track.requesterName || 'N/A';

        lines.push(`\`${num}.\` **${title}**\n　　\`${dur}\` • 👤 ${requester}`);
    }

    const embed = new EmbedBuilder()
        .setColor(0x9B59B6)
        .setTitle('📜 Lịch Sử Phát Nhạc')
        .setDescription(lines.join('\n'))
        .setFooter({
            text: `Hiển thị ${maxDisplay}/${state.history.length} bài gần nhất │ Sử dụng /previous để phát lại bài gần nhất`
        })
        .setTimestamp();

    await interaction.reply({ embeds: [embed] });
}

module.exports = { definition, execute };
