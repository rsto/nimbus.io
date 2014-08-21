package tools

import (
	"io"

	"fog"
)

func ReadAndDiscard(reader io.Reader) {
	const bufferSize = 64 * 1024
	var bytesRead uint64
	var mbReported uint64
	var buffer []byte

	for true {
		buffer = make([]byte, bufferSize)
		n, err := reader.Read(buffer)
		bytesRead += uint64(n)
		if err != nil {
			fog.Error("ReadAndDiscard error after %d bytes read: %s",
				bytesRead, err)
			break
		}
		fog.Debug("ReadAndDiscard read %d bytes", n)
		mbRead := bytesRead / (1024 * 1024)
		if mbRead > mbReported {
			fog.Debug("ReadAndDiscard read %dmb", mbRead)
			mbReported = mbRead
		}
	}
}
