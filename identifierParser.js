// Validates composite identifier syntax: [Category]:[Payload]-[NodeID].[SubTick]
function validateIdentifier(identifier) {
  const regex = /^(\d{2}):(\d{2}(\.\d{2}){10})-([A-Z]{3}\d{0,6})\.(\d{2})$/;
  return regex.test(identifier);
}

module.exports = { validateIdentifier };