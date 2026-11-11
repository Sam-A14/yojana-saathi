import { api } from "./api";
import { type Session, setHouseholdId } from "./session";

/**
 * Where a signed-in person should land. The server is the source of truth, so this works the same
 * on a new phone as on the old one:
 *   no household yet        -> the first setup screen
 *   household, no members   -> add the family
 *   household with members  -> the dashboard
 * It also refreshes the household id kept with the session (a sign-in on a new phone starts with none).
 */
export async function nextPathFor(session: Session): Promise<string> {
  const me = await api.getMe(session.token);
  if (me.household_id !== session.householdId) setHouseholdId(me.household_id);
  if (!me.household_id) return "/setup/basics";
  const members = await api.listMembers({ id: me.household_id, token: session.token });
  return members.length > 0 ? "/dashboard" : "/setup/members";
}
