const maxApi = require("max-api");
const dgram = require("dgram");

const HOST = "127.0.0.1";
const PORT = 22117;
const INSTANCE = process.pid % 65535;
const socket = dgram.createSocket("udp4");

let currentFrame = [];

function send(message) {
    message.instance = INSTANCE;
    const payload = Buffer.from(JSON.stringify(message), "utf8");
    socket.send(payload, PORT, HOST);
}

maxApi.addHandler("path", (...parts) => {
    const path = parts.join(" ");
    if (path) {
        send({ kind: "sample", path });
    }
});

maxApi.addHandler("info", (name, ...values) => {
    if (name === "name") {
        send({ kind: "info", name: values.join(" ") });
    } else if (name === "length") {
        send({ kind: "info", length: Number(values[0]) || 0 });
    }
});

maxApi.addHandler("grain", (...values) => {
    if (values[0] === "clearlow") {
        send({ kind: "grains", points: currentFrame });
        currentFrame = [];
        return;
    }

    const position = Number(values[0]);
    const amplitude = Number(values[1]);
    if (Number.isFinite(position) && Number.isFinite(amplitude) && currentFrame.length < 24) {
        currentFrame.push([
            Math.max(0, Math.min(1, position)),
            Math.max(0, Math.min(1, amplitude))
        ]);
    }
});

maxApi.outlet("instance", INSTANCE);
const announceTimer = setInterval(() => maxApi.outlet("instance", INSTANCE), 2000);
maxApi.addHandler("close", () => {
    clearInterval(announceTimer);
    socket.close();
});
