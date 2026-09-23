/**
 * /shuffle — Xáo trộn hàng đợi.
 */

const { checkPlayer, checkSameVoiceChannel } = require('../utils/permissions');
const queueService = require('../services/queue/QueueService');

const definition = {
    name: 'shuffle',
    description: 'Xáo trộn hàng đợi',
    options: [{
        name: 'mine',
        type: 5, // BOOLEAN
        description: 'Chỉ xáo trộn bài do bạn thêm (mặc định: toàn bộ)',
        required: false
    }]
};

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: playerCheck.error, ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    const player = playerCheck.player;
    if (player.queue.length <= 1) {
        return interaction.reply({ content: '❌ Cần ít nhất 2 bài trong hàng đợi để xáo trộn.', ephemeral: true });
    }

    const mineOnly = interaction.options.getBoolean('mine') || false;
    const requesterId = mineOnly ? interaction.user.id : null;
    const count = queueService.shuffle(player, requesterId);

    if (mineOnly) {
        await interaction.reply(`🔀 Đã xáo trộn **${count}** bài do bạn thêm!`);
    } else {
        await interaction.reply(`🔀 Đã xáo trộn **${count}** bài trong hàng đợi!`);
    }
}

module.exports = { definition, execute };
