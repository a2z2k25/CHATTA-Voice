import { AccessToken, AccessTokenOptions, VideoGrant } from "livekit-server-sdk";
import { NextResponse, NextRequest } from "next/server";

// NOTE: Environment variables can be defined in `.env.local` or passed from voice-mode config
const API_KEY = process.env.LIVEKIT_API_KEY || "devkey";
const API_SECRET = process.env.LIVEKIT_API_SECRET || "secret";
// TODO: Fix environment variable loading - hardcoded for now
const LIVEKIT_URL = "wss://x1:8443"; // process.env.LIVEKIT_URL || "ws://localhost:7880";

// Password protection - set this in your .env.local file
const ACCESS_PASSWORD = process.env.LIVEKIT_ACCESS_PASSWORD || "voicemode123";

// don't cache the results
export const revalidate = 0;

export type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
};

export async function GET(request: NextRequest) {
  try {
    // Check for password in query params or Authorization header
    const url = new URL(request.url);
    const password = url.searchParams.get('password') || 
                    request.headers.get('x-access-password');
    
    if (password !== ACCESS_PASSWORD) {
      return new NextResponse("Unauthorized", { status: 401 });
    }
    
    // These checks are now optional since we have defaults
    // but we can still validate they're not empty strings
    if (!LIVEKIT_URL) {
      throw new Error("LIVEKIT_URL is empty");
    }
    if (!API_KEY) {
      throw new Error("LIVEKIT_API_KEY is empty");
    }
    if (!API_SECRET) {
      throw new Error("LIVEKIT_API_SECRET is empty");
    }

    // Generate participant token
    const participantIdentity = `voice_assistant_user_${Math.floor(Math.random() * 10_000)}`;
    const roomName = `voice_assistant_room_${Math.floor(Math.random() * 10_000)}`;
    const participantToken = await createParticipantToken(
      { identity: participantIdentity },
      roomName
    );

    // Log the URL being used for debugging
    console.log("LIVEKIT_URL from env:", process.env.LIVEKIT_URL);
    console.log("Using LIVEKIT_URL:", LIVEKIT_URL);
    
    // Return connection details
    const data: ConnectionDetails = {
      serverUrl: LIVEKIT_URL,
      roomName,
      participantToken: participantToken,
      participantName: participantIdentity,
    };
    const headers = new Headers({
      "Cache-Control": "no-store",
    });
    return NextResponse.json(data, { headers });
  } catch (error) {
    if (error instanceof Error) {
      console.error(error);
      return new NextResponse(error.message, { status: 500 });
    }
  }
}

function createParticipantToken(userInfo: AccessTokenOptions, roomName: string) {
  const at = new AccessToken(API_KEY, API_SECRET, {
    ...userInfo,
    ttl: "15m",
  });
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };
  at.addGrant(grant);
  return at.toJwt();
}
