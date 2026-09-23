/**
 * PlayerState — Trạng thái phát nhạc tập trung cho từng Guild.
 *
 * Lưu trữ: bài đang phát, lịch sử, chế độ lặp, generation guard,
 * và tham chiếu tin nhắn Now Playing để cập nhật.
 */

/** Số lượng bài hát tối đa lưu trong history */
const MAX_HISTORY = 50;

class PlayerState {
    /**
     * @param {string} guildId - ID của Discord guild
     */
    constructor(guildId) {
        /** ID guild */
        this.guildId = guildId;

        /**
         * Bộ đếm thế hệ phát nhạc (Playback Generation).
         * Tăng lên mỗi khi thực hiện skip/stop/playskip.
         * Các tác vụ resolve bất đồng bộ so sánh generation
         * trước khi phát để tránh phát nhầm bài hát cũ.
         */
        this.playbackGeneration = 0;

        /** Mảng lưu lịch sử các bài hát đã phát (mới nhất ở đầu) */
        this.history = [];

        /** Chế độ lặp: 'off' | 'track' | 'queue' */
        this.repeatMode = 'off';

        /** ID tin nhắn Now Playing hiện tại (để edit thay vì gửi mới) */
        this.nowPlayingMessageId = null;

        /** ID kênh chứa tin nhắn Now Playing */
        this.nowPlayingChannelId = null;

        /** ID interval timer đang cập nhật progress bar (nếu có) */
        this.progressInterval = null;
    }

    /**
     * Tăng playback generation, vô hiệu hoá các resolve cũ đang chờ.
     * @returns {number} Generation mới
     */
    incrementGeneration() {
        return ++this.playbackGeneration;
    }

    /**
     * Kiểm tra xem generation có còn hợp lệ không.
     * @param {number} generation - Generation lúc bắt đầu resolve
     * @returns {boolean} true nếu vẫn hợp lệ
     */
    isGenerationValid(generation) {
        return generation === this.playbackGeneration;
    }

    /**
     * Đẩy bài hát vừa phát xong vào lịch sử (đầu mảng).
     * Giới hạn tối đa MAX_HISTORY bài.
     * @param {object} track - Track object
     */
    addToHistory(track) {
        if (!track) return;
        this.history.unshift(track);
        if (this.history.length > MAX_HISTORY) {
            this.history.pop();
        }
    }

    /**
     * Lấy bài hát gần nhất từ lịch sử (và xoá khỏi history).
     * @returns {object|null} Track hoặc null nếu history trống
     */
    popFromHistory() {
        if (this.history.length === 0) return null;
        return this.history.shift();
    }

    /**
     * Chuyển đổi chế độ lặp theo vòng: off → track → queue → off
     * @returns {string} Chế độ lặp mới
     */
    cycleRepeatMode() {
        const modes = ['off', 'track', 'queue'];
        const currentIndex = modes.indexOf(this.repeatMode);
        this.repeatMode = modes[(currentIndex + 1) % modes.length];
        return this.repeatMode;
    }

    /**
     * Đặt chế độ lặp trực tiếp.
     * @param {'off'|'track'|'queue'} mode
     */
    setRepeatMode(mode) {
        if (['off', 'track', 'queue'].includes(mode)) {
            this.repeatMode = mode;
        }
    }

    /**
     * Dọn dẹp interval và reset tin nhắn Now Playing.
     */
    clearNowPlaying() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        this.nowPlayingMessageId = null;
        this.nowPlayingChannelId = null;
    }

    /**
     * Reset toàn bộ state về mặc định.
     */
    reset() {
        this.clearNowPlaying();
        this.playbackGeneration = 0;
        this.history = [];
        this.repeatMode = 'off';
    }
}

// --- Registry: Quản lý PlayerState theo Guild ---

/** @type {Map<string, PlayerState>} */
const stateMap = new Map();

/**
 * Lấy hoặc tạo PlayerState cho một guild.
 * @param {string} guildId
 * @returns {PlayerState}
 */
function getState(guildId) {
    if (!stateMap.has(guildId)) {
        stateMap.set(guildId, new PlayerState(guildId));
    }
    return stateMap.get(guildId);
}

/**
 * Xóa PlayerState của một guild (khi bot rời khỏi guild).
 * @param {string} guildId
 */
function removeState(guildId) {
    const state = stateMap.get(guildId);
    if (state) {
        state.reset();
        stateMap.delete(guildId);
    }
}

module.exports = {
    PlayerState,
    getState,
    removeState,
    MAX_HISTORY
};
