/**
 * /previous — Phát lại bài hát gần nhất từ lịch sử.
 */

const { checkPlayer, checkSameVoiceChannel } = require('../utils/permissions');

const definition = {
    name: 'previous',
    description: 'Phát lại bài hát vừa nghe gần nhất'
};

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: playerCheck.error, ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    const result = playerService.previous(playerCheck.player);
    if (!result.ok) {
        return interaction.reply({ content: result.error, ephemeral: true });
    }

    await interaction.reply(`⏮️ Đang phát lại: **${result.track.title || 'Unknown'}**`);
}

module.exports = { definition, execute };
