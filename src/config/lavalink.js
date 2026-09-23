/**
 * Cấu hình danh sách Lavalink Nodes (Lavalink v4) & fallback.
 * Đã kiểm tra và xác thực kết nối WebSocket op:ready thành công.
 */

const defaultNodes = [
    {
        name: 'Kasawa_Node',
        url: 'lava2.kasawa.pro:2334',
        auth: 'youshallnotpass',
        secure: false
    },
    {
        name: 'Serenetia_Node',
        url: 'lavalinkv4.serenetia.com:443',
        auth: 'https://seretia.link/discord',
        secure: true
    }
];

let Nodes = [...defaultNodes];

// Nếu người dùng cấu hình node riêng qua biến môi trường trên Render/VPS
if (process.env.LAVALINK_HOST) {
    Nodes.unshift({
        name: 'Custom_Main_Node',
        url: process.env.LAVALINK_HOST,
        auth: process.env.LAVALINK_AUTH || 'youshallnotpass',
        secure: process.env.LAVALINK_SECURE ? process.env.LAVALINK_SECURE === 'true' : true
    });
}

module.exports = { Nodes };

