import { expect, test } from "@playwright/test";
import { ApiError, api, errorKind, limits } from "../../lib/api";

// Saves give up after a time limit instead of leaving "Saving…" up forever, and PATCH / PUT (which
// set fields to the values sent, so doing one twice changes nothing more) are tried once more.
// POST and DELETE are never repeated. Reads are never timed out (a cold server needs its minute).
// These run in Node with fetch replaced, so each case takes a fraction of a second.

const family = { id: "h1", token: "t0ken" };
const realFetch = globalThis.fetch;

type Call = {
  url: string;
  method: string;
  body: string | undefined;
  authorization: string | undefined;
  signal: AbortSignal | undefined;
};
let calls: Call[] = [];

/** What the fake network does with the nth request (1-based): "stall" never answers (until aborted),
 * "ok" answers at once, "fail" is a refused connection, "500" is a server error. */
function network(plan: (attempt: number) => "stall" | "ok" | "fail" | "500" | number) {
  calls = [];
  globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({
      url: String(url),
      method: init?.method ?? "GET",
      body: init?.body as string | undefined,
      authorization: (init?.headers as Record<string, string> | undefined)?.Authorization,
      signal: init?.signal ?? undefined,
    });
    const what = plan(calls.length);
    if (what === "fail") throw new TypeError("Failed to fetch");
    if (what === "500") return new Response("{}", { status: 500 });
    if (typeof what === "number") {
      await new Promise((done) => setTimeout(done, what)); // a slow answer that does arrive
    } else if (what === "stall") {
      await new Promise((_, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      });
    }
    return new Response(JSON.stringify({ id: "h1", documents: {} }), { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
}

test.beforeEach(() => {
  limits.writeTimeoutMs = 60; // 15 seconds in the app; short here
});
test.afterEach(() => {
  globalThis.fetch = realFetch;
  limits.writeTimeoutMs = 15_000;
});

test.describe("a save that stalls", () => {
  test("PATCH: stalled once, then answered: it is tried again and succeeds", async () => {
    network((n) => (n === 1 ? "stall" : "ok"));

    await expect(api.updateHousehold(family, { state: "UP" } as never)).resolves.toBeTruthy();

    expect(calls).toHaveLength(2);
    expect(calls[1]).toMatchObject({ method: "PATCH", url: calls[0].url, body: calls[0].body }); // the same save
    expect(calls[0].signal?.aborted).toBe(true); // the stalled one was given up on
  });

  test("PUT is retried the same way", async () => {
    network((n) => (n === 1 ? "stall" : "ok"));

    await expect(api.setDocuments(family, "m1", { aadhaar_card: true })).resolves.toBeTruthy();

    expect(calls.map((c) => c.method)).toEqual(["PUT", "PUT"]);
  });

  test("PATCH: stalled twice: gives up after exactly two tries with the 'timeout' error", async () => {
    network(() => "stall");

    const error = await api.updateHousehold(family, {} as never).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.timedOut).toBe(true);
    expect(errorKind(error)).toBe("timeout");
    await new Promise((done) => setTimeout(done, 200)); // and nothing tries a third time
    expect(calls).toHaveLength(2);
  });

  test("POST is never retried: one try, then the 'timeout' error", async () => {
    network(() => "stall");

    const error = await api.addMember(family, { nickname: "Asha" } as never).catch((e) => e);

    expect(errorKind(error)).toBe("timeout");
    await new Promise((done) => setTimeout(done, 200));
    expect(calls).toHaveLength(1); // a first try that "timed out" may still have arrived
    expect(calls[0].method).toBe("POST");
  });

  test("DELETE is not retried either", async () => {
    network(() => "stall");

    const error = await api.deleteMember(family, "m1").catch((e) => e);

    expect(errorKind(error)).toBe("timeout");
    await new Promise((done) => setTimeout(done, 200));
    expect(calls).toHaveLength(1);
  });
});

test.describe("everything else is left alone", () => {
  test("a save that answers in time is sent once", async () => {
    network(() => 20); // slower than nothing, faster than the limit

    await api.updateHousehold(family, {} as never);

    expect(calls).toHaveLength(1);
    expect(calls[0].signal?.aborted).toBe(false);
  });

  test("a read is never timed out, however long it takes (a cold server needs its minute)", async () => {
    network(() => 250); // four times the write limit

    await expect(api.getHousehold(family)).resolves.toBeTruthy();

    expect(calls).toHaveLength(1);
    expect(calls[0].signal).toBeUndefined(); // no timer at all
  });

  test("a refused connection is a 'network' error at once and is not retried", async () => {
    network(() => "fail");

    const error = await api.updateHousehold(family, {} as never).catch((e) => e);

    expect(errorKind(error)).toBe("network");
    expect(error.timedOut).toBe(false);
    expect(calls).toHaveLength(1);
  });

  test("a server error is not retried and is not a timeout", async () => {
    network(() => "500");

    const error = await api.updateHousehold(family, {} as never).catch((e) => e);

    expect(errorKind(error)).toBe("generic");
    expect(calls).toHaveLength(1);
  });

  test("the retry still carries the session token and the JSON body", async () => {
    network((n) => (n === 1 ? "stall" : "ok"));

    await api.updateHousehold(family, { district: "Agra" } as never);

    expect(calls).toHaveLength(2);
    for (const call of calls) {
      expect(JSON.parse(call.body!)).toEqual({ district: "Agra" });
      expect(call.authorization).toBe("Bearer t0ken");
    }
  });
});

test("the message kinds: a timeout is its own kind, status 0 without the flag stays 'network'", () => {
  expect(errorKind(new ApiError(0, "x", null, null, true))).toBe("timeout");
  expect(errorKind(new ApiError(0, "x"))).toBe("network");
  expect(errorKind(new ApiError(401, "x"))).toBe("signedOut");
});
