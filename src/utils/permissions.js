/**
 * Permission utilities — Kiểm tra điều kiện Voice Channel và quyền.
 */

/**
 * Kiểm tra xem member có ở trong voice channel hay không.
 * @param {import('discord.js').GuildMember} member
 * @returns {{ ok: boolean, channel?: import('discord.js').VoiceChannel, error?: string }}
 */
function checkVoiceChannel(member) {
    const channel = member.voice?.channel;
    if (!channel) {
        return { ok: false, error: '❌ Bạn cần vào kênh thoại trước!' };
    }
    return { ok: true, channel };
}

/**
 * Kiểm tra xem member có ở CÙNG voice channel với bot hay không.
 * @param {import('discord.js').GuildMember} member
 * @param {object} player - Kazagumo player
 * @returns {{ ok: boolean, error?: string }}
 */
function checkSameVoiceChannel(member, player) {
    const voiceCheck = checkVoiceChannel(member);
    if (!voiceCheck.ok) return voiceCheck;

    if (player && player.voiceId && voiceCheck.channel.id !== player.voiceId) {
        return { ok: false, error: '❌ Bạn cần ở cùng kênh thoại với bot!' };
    }
    return { ok: true, channel: voiceCheck.channel };
}

/**
 * Kiểm tra xem có player đang hoạt động trong guild hay không.
 * @param {import('kazagumo').Kazagumo} manager - Kazagumo manager
 * @param {string} guildId
 * @returns {{ ok: boolean, player?: object, error?: string }}
 */
function checkPlayer(manager, guildId) {
    const player = manager.players.get(guildId);
    if (!player) {
        return { ok: false, error: '❌ Không có kết nối âm thanh.' };
    }
    return { ok: true, player };
}

/**
 * Kiểm tra xem có bài nhạc đang phát không.
 * @param {object} player - Kazagumo player
 * @returns {{ ok: boolean, error?: string }}
 */
function checkPlaying(player) {
    if (!player || (!player.playing && !player.paused)) {
        return { ok: false, error: '❌ Không có bài nào đang phát.' };
    }
    return { ok: true };
}

module.exports = {
    checkVoiceChannel,
    checkSameVoiceChannel,
    checkPlayer,
    checkPlaying
};
