import type { CompanyRole } from "./api";

export type MembershipCheckState = "loading" | "ready" | "error";

type JobApplicationAction = {
  showButton: boolean;
  disabled: boolean;
  label: string;
  membershipMessage: string | null;
};

export function getJobApplicationActionState({
  membershipCheck,
  role,
  applied,
  busy,
}: {
  membershipCheck: MembershipCheckState;
  role: CompanyRole | undefined;
  applied: boolean;
  busy: boolean;
}): JobApplicationAction {
  if (membershipCheck === "ready" && role !== undefined) {
    return {
      showButton: false,
      disabled: true,
      label: "",
      membershipMessage: "Formás parte de esta empresa",
    };
  }
  if (membershipCheck === "loading") {
    return {
      showButton: true,
      disabled: true,
      label: "Verificando...",
      membershipMessage: null,
    };
  }
  if (membershipCheck === "error") {
    return {
      showButton: true,
      disabled: true,
      label: "Postulación no disponible",
      membershipMessage: null,
    };
  }
  if (busy) {
    return {
      showButton: true,
      disabled: true,
      label: "Enviando...",
      membershipMessage: null,
    };
  }
  if (applied) {
    return {
      showButton: true,
      disabled: true,
      label: "Ya te postulaste",
      membershipMessage: null,
    };
  }
  return {
    showButton: true,
    disabled: false,
    label: "Postularme",
    membershipMessage: null,
  };
}
