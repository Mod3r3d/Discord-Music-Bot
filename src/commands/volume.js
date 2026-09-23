/**
 * /volume — Điều chỉnh âm lượng phát nhạc (1 - 200%).
 */

const { checkPlayer, checkSameVoiceChannel } = require('../utils/permissions');
const { getState } = require('../services/player/PlayerState');

const definition = {
    name: 'volume',
    description: 'Xem hoặc điều chỉnh âm lượng phát nhạc (1 - 200%)',
    options: [{
        name: 'level',
        type: 4, // INTEGER
        description: 'Mức âm lượng (từ 1 đến 200%)',
        required: false,
        min_value: 1,
        max_value: 200
    }]
};

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: playerCheck.error, ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    const player = playerCheck.player;
    let level = interaction.options.getInteger('level');

    if (level === null || level === undefined) {
        return interaction.reply(`🔊 Âm lượng hiện tại: **${player.volume || 100}%**`);
    }

    level = Math.max(1, Math.min(200, level));
    await player.setVolume(level);

    // Cập nhật lại giao diện Now Playing nếu đang hiển thị
    const state = getState(interaction.guild.id);
    if (state.nowPlayingMessage && player.queue.current) {
        try {
            const NowPlayingUI = require('../services/ui/NowPlayingUI');
            const updated = NowPlayingUI.create(player, player.queue.current, state);
            await state.nowPlayingMessage.edit({ embeds: [updated.embed], components: updated.components });
        } catch (_) {}
    }

    await interaction.reply(`🔊 Đã chỉnh âm lượng thành: **${level}%**`);
}

module.exports = { definition, execute };
