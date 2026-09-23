/**
 * /stop — Dừng nhạc, xóa hàng đợi, ngắt kết nối.
 */

const { checkPlayer, checkSameVoiceChannel } = require('../utils/permissions');

const definition = {
    name: 'stop',
    description: 'Dừng nhạc và thoát khỏi kênh thoại'
};

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: '❌ Bot không ở trong kênh thoại.', ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    await playerService.stop(playerCheck.player);
    await interaction.reply('🛑 Đã dừng nhạc và xóa toàn bộ hàng đợi.');
}

module.exports = { definition, execute };
