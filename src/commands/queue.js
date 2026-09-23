/**
 * /queue — Xem, quản lý danh sách chờ (view, remove, move, clear).
 */

const { checkPlayer, checkSameVoiceChannel } = require('../utils/permissions');
const queueService = require('../services/queue/QueueService');
const QueueUI = require('../services/ui/QueueUI');

const definition = {
    name: 'queue',
    description: 'Xem và quản lý danh sách chờ',
    options: [
        {
            name: 'page',
            type: 4, // INTEGER
            description: 'Số trang muốn xem (mặc định: 1)',
            required: false
        },
        {
            name: 'remove',
            type: 4, // INTEGER
            description: 'Xóa bài hát tại vị trí này (VD: 3)',
            required: false
        },
        {
            name: 'move_from',
            type: 4,
            description: 'Di chuyển bài: vị trí nguồn',
            required: false
        },
        {
            name: 'move_to',
            type: 4,
            description: 'Di chuyển bài: vị trí đích',
            required: false
        },
        {
            name: 'clear',
            type: 5, // BOOLEAN
            description: 'Xóa toàn bộ hàng đợi (giữ bài đang phát)',
            required: false
        }
    ]
};

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) {
        return interaction.reply({ content: '📭 Không có bài nào trong hàng đợi.', ephemeral: true });
    }

    const player = playerCheck.player;

    // --- /queue clear ---
    const shouldClear = interaction.options.getBoolean('clear');
    if (shouldClear) {
        const voiceCheck = checkSameVoiceChannel(interaction.member, player);
        if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

        const count = queueService.clear(player);
        return interaction.reply(`🗑️ Đã xóa **${count}** bài khỏi hàng đợi. Bài đang phát không bị ảnh hưởng.`);
    }

    // --- /queue remove <index> ---
    const removeIndex = interaction.options.getInteger('remove');
    if (removeIndex !== null && removeIndex !== undefined) {
        const voiceCheck = checkSameVoiceChannel(interaction.member, player);
        if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

        // User nhập 1-based, service dùng 0-based
        const removed = queueService.remove(player, removeIndex - 1);
        if (!removed) {
            return interaction.reply({ content: `❌ Vị trí **${removeIndex}** không hợp lệ.`, ephemeral: true });
        }
        return interaction.reply(`🗑️ Đã xóa: **${removed.title || 'Unknown'}** (vị trí ${removeIndex})`);
    }

    // --- /queue move <from> <to> ---
    const moveFrom = interaction.options.getInteger('move_from');
    const moveTo = interaction.options.getInteger('move_to');
    if (moveFrom !== null && moveFrom !== undefined && moveTo !== null && moveTo !== undefined) {
        const voiceCheck = checkSameVoiceChannel(interaction.member, player);
        if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

        const success = queueService.move(player, moveFrom - 1, moveTo - 1);
        if (!success) {
            return interaction.reply({ content: '❌ Vị trí không hợp lệ.', ephemeral: true });
        }
        return interaction.reply(`↕️ Đã di chuyển bài từ vị trí **${moveFrom}** đến **${moveTo}**`);
    }

    // --- /queue [page] — Hiển thị danh sách ---
    const page = interaction.options.getInteger('page') || 1;
    const { embed, components } = QueueUI.create(player, page);
    await interaction.reply({ embeds: [embed], components });
}

module.exports = { definition, execute };
