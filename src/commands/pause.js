/**
 * /pause — Tạm dừng nhạc.
 */

const { checkPlayer, checkPlaying, checkSameVoiceChannel } = require('../utils/permissions');

const definition = {
    name: 'pause',
    description: 'Tạm dừng nhạc'
};

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: playerCheck.error, ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    const playingCheck = checkPlaying(playerCheck.player);
    if (!playingCheck.ok) return interaction.reply({ content: '❌ Không có bài nào đang phát.', ephemeral: true });

    playerService.pause(playerCheck.player);
    await interaction.reply('⏸️ Đã tạm dừng nhạc!');
}

module.exports = { definition, execute };
